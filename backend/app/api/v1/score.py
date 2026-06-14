from math import comb

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection
from app.schemas.score import CompetitiveScoreOut, SubScore

router = APIRouter(tags=["score"])

_W_CONSISTENCY = 0.40
_W_POWER       = 0.30
_W_META        = 0.20
_W_RESILIENCE  = 0.10


# ── Helpers ───────────────────────────────────────────────────────────────────

def _p_at_least_one(N: int, K: int, n: int = 5) -> float:
    if K <= 0 or N <= 0:
        return 0.0
    if K >= N:
        return 1.0
    denom = comb(N, n)
    return 1 - comb(max(N - K, 0), min(n, N - K)) / denom if denom else 0.0


def _status(v: float) -> str:
    if v >= 75:
        return "strong"
    if v >= 55:
        return "ok"
    if v >= 35:
        return "weak"
    return "critical"


def _grade(score: float) -> str:
    if score >= 85: return "S"
    if score >= 72: return "A"
    if score >= 58: return "B"
    if score >= 42: return "C"
    return "D"


# ── Sub-score calculators ─────────────────────────────────────────────────────

def _consistency_score(
    main_count: int,
    role_totals: dict[str, int],
    has_roles: bool,
) -> SubScore:
    if not has_roles or main_count == 0:
        return SubScore(
            value=50.0,
            label="Consistance",
            weight=_W_CONSISTENCY,
            status="ok",
            note="Rôles non tagués — score estimé à 50/100.",
            tip="Taguez vos cartes (starter, handtrap…) dans le Calculateur de probabilités pour un score précis.",
        )

    S = role_totals.get("starter", 0)
    H = role_totals.get("handtrap", 0)
    non_SH = main_count - S - H

    p_starter  = _p_at_least_one(main_count, S)
    p_handtrap = _p_at_least_one(main_count, H)
    p_dead = comb(max(non_SH, 0), min(5, non_SH)) / comb(main_count, 5) if comb(main_count, 5) > 0 else 0.0

    raw = p_starter * 60 + p_handtrap * 25 + (1 - p_dead) * 15
    value = round(min(raw * 100, 100), 1)

    parts = []
    if p_starter < 0.70:
        parts.append(f"P(starter) = {p_starter*100:.0f}% — faible")
    if p_handtrap < 0.60:
        parts.append(f"P(handtrap) = {p_handtrap*100:.0f}% — faible")
    if p_dead > 0.15:
        parts.append(f"Main morte {p_dead*100:.0f}% — trop élevé")

    note = (
        f"P(starter)={p_starter*100:.0f}% · P(handtrap)={p_handtrap*100:.0f}% · "
        f"Main morte={p_dead*100:.0f}%"
    )

    tip = None
    if parts:
        tip = " | ".join(parts) + ". Consultez le Ratio Advisor pour ajuster."

    return SubScore(value=value, label="Consistance", weight=_W_CONSISTENCY, status=_status(value), note=note, tip=tip)


def _power_score(
    extra_count: int,
    role_totals: dict[str, int],
    has_roles: bool,
) -> SubScore:
    boss  = role_totals.get("boss", 0) if has_roles else 0
    start = role_totals.get("starter", 0) if has_roles else 0
    ext   = role_totals.get("extender", 0) if has_roles else 0

    extra_completeness = min(extra_count / 15, 1.0) * 50
    boss_score         = min(boss / 3, 1.0) * 30
    engine_score       = min((start + ext) / 12, 1.0) * 20

    value = round(extra_completeness + boss_score + engine_score, 1)

    if not has_roles:
        note = f"Extra deck {extra_count}/15. Taguez les boss monsters pour affiner."
        tip = "Taguez vos boss monsters (rôle 'boss') pour un score de puissance précis."
    else:
        note = f"Extra {extra_count}/15 · {boss} boss · {start + ext} starters+extenders"
        tip = None
        if extra_count < 12:
            tip = f"Extra deck léger ({extra_count}/15). Complétez avec des génériques (Baronne, Apollousa, Tri-Brigade…)."
        elif boss == 0:
            tip = "Aucun boss monster tagué. Taguez vos win-cons en rôle 'boss'."

    return SubScore(value=value, label="Puissance", weight=_W_POWER, status=_status(value), note=note, tip=tip)


async def _meta_score(
    db: AsyncSession,
    deck_id: int,
    archetype_label: str | None,
    main_card_ids: list[int],
) -> SubScore:
    if not main_card_ids:
        return SubScore(value=50.0, label="Position méta", weight=_W_META, status="ok",
                        note="Deck vide.", tip=None)

    # Build presence map: card_id → global presence % across all other decks
    sql = text("""
        WITH other_subs AS (
            SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id, ds.deck_id
            FROM deck_submissions ds
            WHERE ds.deck_id != :deck_id
            ORDER BY ds.deck_id, ds.created_at DESC
        ),
        total AS (SELECT COUNT(*) AS n FROM other_subs),
        presence AS (
            SELECT dc.card_id, COUNT(DISTINCT os.deck_id) AS cnt
            FROM other_subs os
            JOIN deck_cards dc ON dc.deck_submission_id = os.sub_id
                               AND dc.section = 'main'
            WHERE dc.card_id = ANY(:card_ids)
            GROUP BY dc.card_id
        )
        SELECT p.card_id, ROUND(p.cnt::numeric / NULLIF(t.n, 0), 4) AS pct
        FROM presence p CROSS JOIN total t
    """)

    rows = (await db.execute(sql, {"deck_id": deck_id, "card_ids": main_card_ids})).fetchall()

    total_decks_sql = await db.execute(
        text("SELECT COUNT(DISTINCT deck_id) FROM deck_submissions WHERE deck_id != :did"),
        {"did": deck_id}
    )
    total_other = total_decks_sql.scalar() or 0

    if total_other == 0:
        return SubScore(
            value=50.0, label="Position méta", weight=_W_META, status="ok",
            note="Pas assez de decks en base pour calculer la position méta.",
            tip="Importez plus de decklists pour enrichir l'analyse méta.",
        )

    presence_map = {row.card_id: float(row.pct or 0) for row in rows}

    # Average presence of deck's main cards across all other decks
    avg_presence = sum(presence_map.get(cid, 0) for cid in main_card_ids) / len(main_card_ids)
    value = round(min(avg_presence * 200, 100), 1)  # scale: 50% global presence → 100 score

    arch_note = f" (archétype : {archetype_label})" if archetype_label else ""
    note = f"Présence moyenne de vos cartes dans les {total_other} autre(s) deck(s){arch_note} : {avg_presence*100:.1f}%"

    tip = None
    if value < 40:
        tip = "Peu de vos cartes sont jouées ailleurs. Deck original ou peu méta — risque d'être sous-optimal contre le top."
    elif value > 80:
        tip = "Deck très aligné avec le méta actuel."

    return SubScore(value=value, label="Position méta", weight=_W_META, status=_status(value), note=note, tip=tip)


def _resilience_score(
    main_count: int,
    role_totals: dict[str, int],
    has_roles: bool,
    trap_count: int,
) -> SubScore:
    if not has_roles or main_count == 0:
        # Proxy: fewer traps = more proactive = more resilient
        proxy = max(0.0, 1.0 - trap_count / max(main_count, 1)) * 0.5 + 0.25
        value = round(min(proxy * 100, 100), 1)
        return SubScore(
            value=value, label="Résilience", weight=_W_RESILIENCE, status=_status(value),
            note="Estimé à partir des traps (sans rôles tagués).",
            tip="Taguez starters, extenders et garnets pour un score précis.",
        )

    S = role_totals.get("starter", 0)
    E = role_totals.get("extender", 0)
    G = role_totals.get("garnet", 0)
    denom = S + E + G

    if denom == 0:
        return SubScore(value=50.0, label="Résilience", weight=_W_RESILIENCE, status="ok",
                        note="Pas de starters/extenders/garnets tagués.", tip=None)

    raw = (S + E) / denom
    value = round(raw * 100, 1)

    note = f"{S} starters + {E} extenders vs {G} garnets → {value:.0f}/100"
    tip = None
    if G > 3:
        tip = f"{G} garnets réduisent la résilience. Visez ≤ 3 garnets pour une combabilité maximale."
    elif S + E < 8:
        tip = "Peu de starters/extenders. Le deck perd en fonctionnalité après une disruption adverse."

    return SubScore(value=value, label="Résilience", weight=_W_RESILIENCE, status=_status(value), note=note, tip=tip)


def _summary(global_score: float, subs: list[SubScore]) -> str:
    weakest = min(subs, key=lambda s: s.value)
    if global_score >= 80:
        return f"Deck de haut niveau. Point à surveiller : {weakest.label.lower()} ({weakest.value:.0f}/100)."
    if global_score >= 60:
        return f"Deck solide mais perfectible. Principal levier : améliorer la {weakest.label.lower()} ({weakest.value:.0f}/100)."
    if global_score >= 40:
        return f"Deck en développement. Priorité : {weakest.label.lower()} ({weakest.value:.0f}/100)."
    return f"Deck fragile. Commencez par renforcer la {weakest.label.lower()} ({weakest.value:.0f}/100)."


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/{deck_id}/score", response_model=CompetitiveScoreOut)
async def competitive_score(
    deck_id: int,
    db: AsyncSession = Depends(get_db),
) -> CompetitiveScoreOut:
    """Compute a 0-100 competitive score across 4 dimensions."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    sub = await db.scalar(
        select(DeckSubmission)
        .where(DeckSubmission.deck_id == deck_id)
        .options(selectinload(DeckSubmission.cards).selectinload(DeckCard.card))
        .order_by(DeckSubmission.created_at.desc())
        .limit(1)
    )
    if not sub:
        raise HTTPException(status_code=404, detail=f"No submission found for deck {deck_id}")

    # Aggregate main deck stats
    main_count = extra_count = trap_count = 0
    role_totals: dict[str, int] = {}
    has_roles = False
    main_card_ids: list[int] = []

    for dc in sub.cards:
        qty = dc.quantity
        if dc.section == CardSection.main:
            main_count += qty
            card = dc.card
            ft = (card.frame_type or "").lower()
            ct = card.type or ""
            if ft == "trap" or "Trap" in ct:
                trap_count += qty
            if dc.role is not None:
                has_roles = True
                role_totals[dc.role] = role_totals.get(dc.role, 0) + qty
            main_card_ids.extend([dc.card.id] * qty)
        elif dc.section == CardSection.extra:
            extra_count += qty

    # Deduplicate main_card_ids for meta query (use distinct IDs)
    unique_main_ids = list({c for c in main_card_ids})

    consistency = _consistency_score(main_count, role_totals, has_roles)
    power       = _power_score(extra_count, role_totals, has_roles)
    meta        = await _meta_score(db, deck_id, deck.archetype_label, unique_main_ids)
    resilience  = _resilience_score(main_count, role_totals, has_roles, trap_count)

    global_score = round(
        consistency.value * _W_CONSISTENCY
        + power.value * _W_POWER
        + meta.value * _W_META
        + resilience.value * _W_RESILIENCE,
        1,
    )

    subs = [consistency, power, meta, resilience]

    return CompetitiveScoreOut(
        deck_id=deck_id,
        deck_title=deck.title,
        global_score=global_score,
        grade=_grade(global_score),
        has_roles=has_roles,
        consistency=consistency,
        power=power,
        meta=meta,
        resilience=resilience,
        summary=_summary(global_score, subs),
    )
