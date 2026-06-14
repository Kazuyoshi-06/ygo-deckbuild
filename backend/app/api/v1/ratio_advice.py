from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.database import get_db
from app.models import Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection
from app.schemas.ratio_advice import AdviceItem, ArchetypeAverages, RatioAdviceOut

router = APIRouter(tags=["ratio-advice"])

# ── Reference ranges (TCG 2025-2026 competitive) ──────────────────────────────

_REFS = {
    "main_count": (40, 42, 40, 60),         # ideal_min, ideal_max, warn_min, warn_max
    "monster":    (20, 24, 18, 26),
    "spell":      (10, 14,  8, 16),
    "trap":       ( 3,  8,  0, 12),
    "extra":      (12, 15,  0, 15),
    "side":       ( 0, 15,  0, 15),
}

_ROLE_REFS = {
    "starter":   (9, 15, 6, 18),
    "extender":  (3,  8, 2, 12),
    "handtrap":  (6, 12, 4, 15),
    "garnet":    (0,  3, 0,  5),
    "tech":      (1,  6, 0,  8),
}

_LABELS = {
    "main_count": "Main deck (total)",
    "monster":    "Monsters",
    "spell":      "Spells",
    "trap":       "Traps",
    "extra":      "Extra deck",
    "side":       "Side deck",
    "starter":    "Starters",
    "extender":   "Extenders",
    "handtrap":   "Handtraps",
    "garnet":     "Garnets",
    "tech":       "Tech cards",
}


def _is_spell(frame_type: str, card_type: str) -> bool:
    return frame_type == "spell" or "Spell" in (card_type or "")


def _is_trap(frame_type: str, card_type: str) -> bool:
    return frame_type == "trap" or "Trap" in (card_type or "")


def _status(value: int, ideal_min: int, ideal_max: int, warn_min: int, warn_max: int) -> str:
    if ideal_min <= value <= ideal_max:
        return "ok"
    if warn_min <= value <= warn_max:
        return "warning"
    return "critical"


def _tip(category: str, value: int, ideal_min: int, ideal_max: int, avg: float | None) -> str | None:
    tips: list[str] = []

    if value < ideal_min:
        diff = ideal_min - value
        if category == "main_count":
            tips.append(f"Main trop petit ({value}). Minimum compétitif : 40.")
        elif category == "monster":
            tips.append(f"+{diff} monster(s) recommandé(s). Les decks compétitifs jouent 20-24 monstres.")
        elif category == "spell":
            tips.append(f"+{diff} spell(s) pour atteindre la fourchette compétitive (10-14).")
        elif category == "trap":
            if value == 0:
                tips.append("Aucun trap — ok pour les decks combo purs, risqué sinon.")
        elif category == "extra":
            tips.append(f"Extra deck léger ({value}/15). Complétez avec des génériques (Baronne, Apollousa, Knightmare Unicorn…).")
        elif category == "starter":
            tips.append(f"Seulement {value} starters — risque de mains sans combo. Cible : 9-15.")
        elif category == "handtrap":
            tips.append(f"{value} handtraps — vulnérable aux combos adverses. Cible compétitive : 6-12.")
        elif category == "extender":
            tips.append(f"Peu d'extenders ({value}). Les combos s'arrêteront souvent sur une seule interaction adverse.")

    elif value > ideal_max:
        diff = value - ideal_max
        if category == "main_count":
            tips.append(f"Main surdimensionné ({value}). Idéal : 40-42 pour maximiser la consistance.")
        elif category == "monster":
            tips.append(f"Beaucoup de monstres ({value}). Risque de mains sans spell/trap d'accès.")
        elif category == "spell":
            tips.append(f"Beaucoup de spells ({value}). Vérifiez qu'ils sont tous actionnables en opening hand.")
        elif category == "trap":
            tips.append(f"{value} traps est élevé pour 2026. Les traps sont lents face aux combos modernes.")
        elif category == "garnet":
            tips.append(f"{value} garnets dans le main — chaque garnet réduit la probabilité d'opener d'environ 1.5-2 points. Max recommandé : 3.")
        elif category == "starter":
            tips.append(f"{value} starters peut causer des mains trop «mono-combo» — évaluez les doublons.")

    if avg is not None:
        delta = value - avg
        if abs(delta) >= 2:
            direction = "au-dessus" if delta > 0 else "en-dessous"
            tips.append(f"{abs(delta):.1f} de {direction} de la moyenne des decks du même archétype ({avg:.1f}).")

    return " ".join(tips) if tips else None


async def _archetype_averages(db: AsyncSession, archetype_label: str, exclude_deck_id: int) -> ArchetypeAverages | None:
    """Compute type-ratio averages over the latest submission of each same-archetype deck."""
    sql = text("""
        WITH latest_subs AS (
            SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id, ds.deck_id
            FROM deck_submissions ds
            JOIN decks d ON d.id = ds.deck_id
            WHERE d.archetype_label = :archetype
              AND d.id != :exclude_id
            ORDER BY ds.deck_id, ds.created_at DESC
        ),
        per_deck AS (
            SELECT
                ls.deck_id,
                SUM(CASE WHEN dc.section = 'main' THEN dc.quantity ELSE 0 END)  AS main_count,
                SUM(CASE WHEN dc.section = 'extra' THEN dc.quantity ELSE 0 END) AS extra_count,
                SUM(CASE WHEN dc.section = 'side'  THEN dc.quantity ELSE 0 END) AS side_count,
                SUM(CASE WHEN dc.section = 'main'
                          AND c.frame_type NOT IN ('spell', 'trap')
                          AND c.type NOT LIKE '%%Spell%%'
                          AND c.type NOT LIKE '%%Trap%%'
                          THEN dc.quantity ELSE 0 END) AS monster_count,
                SUM(CASE WHEN dc.section = 'main'
                          AND (c.frame_type = 'spell' OR c.type LIKE '%%Spell%%')
                          THEN dc.quantity ELSE 0 END) AS spell_count,
                SUM(CASE WHEN dc.section = 'main'
                          AND (c.frame_type = 'trap' OR c.type LIKE '%%Trap%%')
                          THEN dc.quantity ELSE 0 END) AS trap_count
            FROM latest_subs ls
            JOIN deck_cards dc ON dc.deck_submission_id = ls.sub_id
            JOIN cards c ON c.id = dc.card_id
            GROUP BY ls.deck_id
        )
        SELECT
            COUNT(*)           AS sample_size,
            AVG(main_count)    AS avg_main,
            AVG(monster_count) AS avg_monster,
            AVG(spell_count)   AS avg_spell,
            AVG(trap_count)    AS avg_trap,
            AVG(extra_count)   AS avg_extra,
            AVG(side_count)    AS avg_side
        FROM per_deck
    """)

    row = (await db.execute(sql, {"archetype": archetype_label, "exclude_id": exclude_deck_id})).one()

    if row.sample_size == 0:
        return None

    return ArchetypeAverages(
        sample_size=int(row.sample_size),
        avg_main=round(float(row.avg_main or 0), 1),
        avg_monster=round(float(row.avg_monster or 0), 1),
        avg_spell=round(float(row.avg_spell or 0), 1),
        avg_trap=round(float(row.avg_trap or 0), 1),
        avg_extra=round(float(row.avg_extra or 0), 1),
        avg_side=round(float(row.avg_side or 0), 1),
    )


def _build_advice(
    type_ratios: dict[str, int],
    role_counts: dict[str, int] | None,
    arch_avgs: ArchetypeAverages | None,
) -> list[AdviceItem]:
    items: list[AdviceItem] = []

    # Type-based categories (always available)
    type_keys = [
        ("main_count", type_ratios["main_count"], getattr(arch_avgs, "avg_main", None) if arch_avgs else None),
        ("monster",    type_ratios["monster"],    getattr(arch_avgs, "avg_monster", None) if arch_avgs else None),
        ("spell",      type_ratios["spell"],      getattr(arch_avgs, "avg_spell", None) if arch_avgs else None),
        ("trap",       type_ratios["trap"],       getattr(arch_avgs, "avg_trap", None) if arch_avgs else None),
        ("extra",      type_ratios["extra"],      getattr(arch_avgs, "avg_extra", None) if arch_avgs else None),
        ("side",       type_ratios["side"],       getattr(arch_avgs, "avg_side", None) if arch_avgs else None),
    ]

    for cat, val, avg in type_keys:
        ideal_min, ideal_max, warn_min, warn_max = _REFS[cat]
        items.append(AdviceItem(
            category=cat,
            label=_LABELS[cat],
            your_value=val,
            archetype_avg=avg,
            archetype_sample=arch_avgs.sample_size if arch_avgs else 0,
            ref_ideal_min=ideal_min,
            ref_ideal_max=ideal_max,
            status=_status(val, ideal_min, ideal_max, warn_min, warn_max),
            tip=_tip(cat, val, ideal_min, ideal_max, avg),
        ))

    # Role-based categories (only if roles tagged)
    if role_counts:
        for role, (ideal_min, ideal_max, warn_min, warn_max) in _ROLE_REFS.items():
            val = role_counts.get(role, 0)
            if val == 0 and role not in ("garnet",):
                # Only show 0-value roles for garnet (where 0 is the target)
                # Skip other zero-count roles to avoid noise
                continue
            items.append(AdviceItem(
                category=role,
                label=_LABELS.get(role, role.capitalize()),
                your_value=val,
                archetype_avg=None,   # role averages require tagged archetypes — out of scope for D3
                archetype_sample=0,
                ref_ideal_min=ideal_min,
                ref_ideal_max=ideal_max,
                status=_status(val, ideal_min, ideal_max, warn_min, warn_max),
                tip=_tip(role, val, ideal_min, ideal_max, None),
            ))

    return items


@router.get("/{deck_id}/ratio-advice", response_model=RatioAdviceOut)
async def get_ratio_advice(
    deck_id: int,
    db: AsyncSession = Depends(get_db),
) -> RatioAdviceOut:
    """Compare deck ratios against competitive reference ranges and same-archetype averages."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    # Latest submission
    sub = await db.scalar(
        select(DeckSubmission)
        .where(DeckSubmission.deck_id == deck_id)
        .options(selectinload(DeckSubmission.cards).selectinload(DeckCard.card))
        .order_by(DeckSubmission.created_at.desc())
        .limit(1)
    )
    if not sub:
        raise HTTPException(status_code=404, detail=f"No submission found for deck {deck_id}")

    # Compute type ratios
    main_count = monster = spell = trap = extra = side = 0
    role_totals: dict[str, int] = {}
    has_roles = False

    for dc in sub.cards:
        card = dc.card
        qty = dc.quantity
        if dc.section == CardSection.main:
            main_count += qty
            if _is_spell(card.frame_type or "", card.type or ""):
                spell += qty
            elif _is_trap(card.frame_type or "", card.type or ""):
                trap += qty
            else:
                monster += qty
        elif dc.section == CardSection.extra:
            extra += qty
        else:
            side += qty

        if dc.role is not None:
            has_roles = True
            role_totals[dc.role] = role_totals.get(dc.role, 0) + qty

    type_ratios = {
        "main_count": main_count,
        "monster": monster,
        "spell": spell,
        "trap": trap,
        "extra": extra,
        "side": side,
    }

    # Archetype averages from DB
    arch_avgs: ArchetypeAverages | None = None
    if deck.archetype_label:
        arch_avgs = await _archetype_averages(db, deck.archetype_label, deck_id)

    advice = _build_advice(type_ratios, role_totals if has_roles else None, arch_avgs)

    return RatioAdviceOut(
        deck_id=deck.id,
        deck_title=deck.title,
        archetype_label=deck.archetype_label,
        main_count=main_count,
        monster_count=monster,
        spell_count=spell,
        trap_count=trap,
        extra_count=extra,
        side_count=side,
        role_counts=role_totals if has_roles else None,
        archetype_averages=arch_avgs,
        advice=advice,
    )
