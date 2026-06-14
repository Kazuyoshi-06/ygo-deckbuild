import random
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection
from app.schemas.simulation import CardBrickRate, SimulationOut, StarterDistEntry

router = APIRouter(tags=["simulation"])

_MAX_SIMULATIONS = 50_000
_DEFAULT_SIMULATIONS = 10_000


def _run_monte_carlo(
    deck: list[dict],   # list of {"card_id", "name", "role"}
    n: int,
    hand_size: int,
) -> SimulationOut:
    wins = mediums = deads = 0
    starter_counts = defaultdict(int)   # count of starters in hand → frequency
    total_starters = total_handtraps = total_garnets = 0

    # card_id → {total, dead}
    card_appearances: dict[int, list[int]] = {c["card_id"]: [0, 0] for c in deck}
    card_meta = {c["card_id"]: c for c in deck}
    seen_ids = list(card_appearances.keys())

    # Build expanded deck (flat list of card_ids, one per copy)
    flat = [c["card_id"] for c in deck]

    for _ in range(n):
        hand = random.sample(flat, min(hand_size, len(flat)))

        n_starters = n_handtraps = n_garnets = 0
        for cid in hand:
            role = card_meta[cid]["role"]
            if role == "starter":
                n_starters += 1
            elif role == "handtrap":
                n_handtraps += 1
            elif role == "garnet":
                n_garnets += 1

        total_starters += n_starters
        total_handtraps += n_handtraps
        total_garnets += n_garnets
        starter_counts[min(n_starters, 3)] += 1

        is_dead = n_starters == 0 and n_handtraps == 0
        if n_starters >= 1:
            wins += 1
        elif n_handtraps >= 1:
            mediums += 1
        else:
            deads += 1

        seen_in_hand: set[int] = set()
        for cid in hand:
            if cid not in seen_in_hand:
                card_appearances[cid][0] += 1
                if is_dead:
                    card_appearances[cid][1] += 1
                seen_in_hand.add(cid)

    starter_dist = [
        StarterDistEntry(
            count=k,
            simulations=starter_counts[k],
            pct=round(starter_counts[k] / n, 4),
        )
        for k in sorted(starter_counts)
    ]

    brick_cards = [
        CardBrickRate(
            card_id=cid,
            name=card_meta[cid]["name"],
            role=card_meta[cid]["role"],
            total_appearances=totals[0],
            dead_appearances=totals[1],
            dead_pct=round(totals[1] / totals[0], 4) if totals[0] > 0 else 0.0,
        )
        for cid, totals in card_appearances.items()
        if totals[0] > 0
    ]
    brick_cards.sort(key=lambda c: -c.dead_pct)

    return SimulationOut(
        deck_id=0,
        deck_title="",
        main_count=len(flat),
        n_simulations=n,
        hand_size=hand_size,
        has_roles=any(c["role"] is not None for c in deck),
        win_rate=round(wins / n, 4),
        medium_rate=round(mediums / n, 4),
        dead_rate=round(deads / n, 4),
        avg_starters=round(total_starters / n, 2),
        avg_handtraps=round(total_handtraps / n, 2),
        avg_garnets=round(total_garnets / n, 2),
        starter_dist=starter_dist,
        brick_cards=brick_cards,
    )


@router.get("/{deck_id}/simulate", response_model=SimulationOut)
async def simulate(
    deck_id: int,
    n: int = Query(default=_DEFAULT_SIMULATIONS, ge=100, le=_MAX_SIMULATIONS, description="Number of simulations"),
    hand: int = Query(default=5, ge=5, le=6, description="Hand size (5=going first, 6=going second)"),
    db: AsyncSession = Depends(get_db),
) -> SimulationOut:
    """Run a Monte Carlo simulation of opening hands for a deck."""
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

    # Build flat deck: expand each DeckCard by quantity
    flat_deck: list[dict] = []
    for dc in sub.cards:
        if dc.section != CardSection.main:
            continue
        for _ in range(dc.quantity):
            flat_deck.append({
                "card_id": dc.card.id,
                "name": dc.card.name,
                "role": dc.role,
            })

    if len(flat_deck) < hand:
        raise HTTPException(status_code=422, detail=f"Main deck too small to simulate ({len(flat_deck)} cards)")

    result = _run_monte_carlo(flat_deck, n, hand)
    result.deck_id = deck_id
    result.deck_title = deck.title
    return result
