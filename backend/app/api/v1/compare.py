from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection
from app.schemas.compare import CompareOut, ComparedCard, DeckMeta, DeckRatios

router = APIRouter(tags=["compare"])

_MIN_DECKS = 2
_MAX_DECKS = 5


def _is_spell(frame_type: str, card_type: str) -> bool:
    return frame_type == "spell" or "Spell" in (card_type or "")


def _is_trap(frame_type: str, card_type: str) -> bool:
    return frame_type == "trap" or "Trap" in (card_type or "")


@router.get("", response_model=CompareOut)
async def compare_decks(
    deck_ids: str = Query(..., description="Comma-separated deck IDs (2–5)"),
    db: AsyncSession = Depends(get_db),
) -> CompareOut:
    """Compare 2 to 5 decklists: core/flex/unique cards, ratios, divergence score."""
    try:
        ids = [int(x.strip()) for x in deck_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="deck_ids must be comma-separated integers")

    if len(ids) < _MIN_DECKS or len(ids) > _MAX_DECKS:
        raise HTTPException(
            status_code=422,
            detail=f"Provide between {_MIN_DECKS} and {_MAX_DECKS} deck IDs",
        )

    # Deduplicate while preserving order
    seen: set[int] = set()
    unique_ids: list[int] = []
    for did in ids:
        if did not in seen:
            seen.add(did)
            unique_ids.append(did)
    ids = unique_ids

    # Load decks
    decks = []
    for did in ids:
        deck = await db.get(Deck, did)
        if not deck:
            raise HTTPException(status_code=404, detail=f"Deck {did} not found")
        decks.append(deck)

    # Load latest submission (with cards) for each deck
    submissions: dict[int, DeckSubmission | None] = {}
    for deck in decks:
        sub = await db.scalar(
            select(DeckSubmission)
            .where(DeckSubmission.deck_id == deck.id)
            .options(selectinload(DeckSubmission.cards).selectinload(DeckCard.card))
            .order_by(DeckSubmission.created_at.desc())
            .limit(1)
        )
        submissions[deck.id] = sub

    # Build card presence map: card_id → {deck_id: total_qty, card_obj}
    # Aggregate across ALL sections for presence comparison
    card_info: dict[int, dict] = {}

    for deck in decks:
        sub = submissions.get(deck.id)
        if not sub:
            continue
        totals: dict[int, int] = {}
        for dc in sub.cards:
            totals[dc.card.id] = totals.get(dc.card.id, 0) + dc.quantity

        for card_id, qty in totals.items():
            if card_id not in card_info:
                card_info[card_id] = {"card": dc.card, "per_deck": {}}
            card_info[card_id]["per_deck"][deck.id] = qty
            card_info[card_id]["card"] = next(
                dc.card for dc in sub.cards if dc.card.id == card_id
            )

    n = len(ids)

    # Classify each card by presence percentage
    core: list[ComparedCard] = []
    flex: list[ComparedCard] = []
    unique: list[ComparedCard] = []

    for card_id, info in card_info.items():
        card = info["card"]
        per_deck: dict[int, int] = info["per_deck"]
        n_present = len(per_deck)
        presence_pct = n_present / n * 100
        quantities = [per_deck.get(did, 0) for did in ids]

        entry = ComparedCard(
            card_id=card.id,
            external_card_id=card.external_card_id,
            name=card.name,
            type=card.type or "",
            frame_type=card.frame_type or "",
            image_url=f"/api/v1/cards/{card.id}/image",
            presence_pct=round(presence_pct, 1),
            quantities=quantities,
        )

        if n_present == n:
            core.append(entry)
        elif presence_pct >= 50:
            flex.append(entry)
        else:
            unique.append(entry)

    core.sort(key=lambda c: c.name)
    flex.sort(key=lambda c: (-c.presence_pct, c.name))
    unique.sort(key=lambda c: (-c.presence_pct, c.name))

    # Compute ratios per deck (main deck section breakdown)
    ratios: list[DeckRatios] = []
    for deck in decks:
        sub = submissions.get(deck.id)
        if not sub:
            ratios.append(DeckRatios())
            continue

        monsters = spells = traps = main_total = extra_total = side_total = 0
        for dc in sub.cards:
            card = dc.card
            qty = dc.quantity
            if dc.section == CardSection.main:
                main_total += qty
                if _is_spell(card.frame_type or "", card.type or ""):
                    spells += qty
                elif _is_trap(card.frame_type or "", card.type or ""):
                    traps += qty
                else:
                    monsters += qty
            elif dc.section == CardSection.extra:
                extra_total += qty
            else:
                side_total += qty

        ratios.append(DeckRatios(
            main_count=main_total,
            monster_count=monsters,
            spell_count=spells,
            trap_count=traps,
            extra_count=extra_total,
            side_count=side_total,
        ))

    # Divergence score: 1 − mean(Jaccard similarity for all pairs)
    def card_set(did: int) -> set[int]:
        return {cid for cid, info in card_info.items() if did in info["per_deck"]}

    pairs = [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]
    if pairs:
        sims = []
        for a, b in pairs:
            sa, sb = card_set(a), card_set(b)
            union = len(sa | sb)
            sims.append(len(sa & sb) / union if union > 0 else 1.0)
        divergence = round(1 - sum(sims) / len(sims), 3)
    else:
        divergence = 0.0

    return CompareOut(
        deck_ids=ids,
        decks=[
            DeckMeta(
                id=d.id,
                title=d.title,
                archetype_label=d.archetype_label,
                tags=d.tags or [],
                created_at=d.created_at,
            )
            for d in decks
        ],
        core=core,
        flex=flex,
        unique=unique,
        ratios=ratios,
        divergence_score=divergence,
    )
