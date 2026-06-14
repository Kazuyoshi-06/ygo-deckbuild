from math import comb

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection
from app.schemas.probability import (
    CardProbRow,
    DeckCardRoleIn,
    GroupStats,
    ProbabilityOut,
    Recommendation,
)

router = APIRouter(tags=["probability"])

ROLE_ORDER = ["starter", "extender", "handtrap", "garnet", "tech", "boss", "other"]


def _p_at_least_one(N: int, K: int, n: int) -> float:
    """P(≥1 successes) drawing n cards from N total with K successes."""
    if K <= 0 or N <= 0 or n <= 0:
        return 0.0
    if K >= N:
        return 1.0
    denom = comb(N, n)
    if denom == 0:
        return 0.0
    return round(1 - comb(max(N - K, 0), min(n, N - K)) / denom, 4)


async def _latest_submission(db: AsyncSession, deck_id: int) -> DeckSubmission:
    sub = await db.scalar(
        select(DeckSubmission)
        .where(DeckSubmission.deck_id == deck_id)
        .options(selectinload(DeckSubmission.cards).selectinload(DeckCard.card))
        .order_by(DeckSubmission.created_at.desc())
        .limit(1)
    )
    if not sub:
        raise HTTPException(status_code=404, detail=f"No submission found for deck {deck_id}")
    return sub


@router.patch("/{deck_id}/cards/{card_id}/role", status_code=204)
async def set_card_role(
    deck_id: int,
    card_id: int,
    body: DeckCardRoleIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    """Assign a competitive role to a card in the deck's latest submission."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    sub = await _latest_submission(db, deck_id)

    result = await db.execute(
        select(DeckCard).where(
            DeckCard.deck_submission_id == sub.id,
            DeckCard.card_id == card_id,
        )
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Card {card_id} not found in deck {deck_id}")

    await db.execute(
        update(DeckCard)
        .where(
            DeckCard.deck_submission_id == sub.id,
            DeckCard.card_id == card_id,
        )
        .values(role=body.role)
    )
    await db.commit()


@router.get("/{deck_id}/probability", response_model=ProbabilityOut)
async def get_probability(
    deck_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProbabilityOut:
    """Compute hypergeometric opening hand probabilities for a deck."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    sub = await _latest_submission(db, deck_id)

    # Aggregate main deck cards by card_id
    main_totals: dict[int, dict] = {}
    for dc in sub.cards:
        if dc.section != CardSection.main:
            continue
        cid = dc.card.id
        if cid not in main_totals:
            main_totals[cid] = {
                "card": dc.card,
                "qty": 0,
                "role": dc.role,
            }
        main_totals[cid]["qty"] += dc.quantity
        # Last role wins (should be same across rows for same card)
        if dc.role is not None:
            main_totals[cid]["role"] = dc.role

    N = sum(info["qty"] for info in main_totals.values())
    has_roles = any(info["role"] is not None for info in main_totals.values())

    # Build per-card probability rows
    cards: list[CardProbRow] = []
    for info in main_totals.values():
        card = info["card"]
        K = info["qty"]
        row = CardProbRow(
            card_id=card.id,
            external_card_id=card.external_card_id,
            name=card.name,
            frame_type=card.frame_type or "",
            image_url=f"/api/v1/cards/{card.id}/image",
            total_in_main=K,
            role=info["role"],
            p_at_least_one_5=_p_at_least_one(N, K, 5),
            p_at_least_one_6=_p_at_least_one(N, K, 6),
            p_zero_5=round(comb(max(N - K, 0), min(5, N - K)) / comb(N, 5), 4) if comb(N, 5) > 0 else 1.0,
        )
        cards.append(row)

    cards.sort(key=lambda c: (ROLE_ORDER.index(c.role) if c.role in ROLE_ORDER else 99, c.name))

    # Group stats by role
    role_totals: dict[str, int] = {}
    for info in main_totals.values():
        r = info["role"]
        if r is not None:
            role_totals[r] = role_totals.get(r, 0) + info["qty"]

    groups: list[GroupStats] = []
    for role in ROLE_ORDER:
        K_group = role_totals.get(role, 0)
        if K_group == 0:
            continue
        groups.append(GroupStats(
            role=role,
            total_copies=K_group,
            p_at_least_one_5=_p_at_least_one(N, K_group, 5),
            p_at_least_one_6=_p_at_least_one(N, K_group, 6),
        ))

    # Dead hand: P(0 starters AND 0 handtraps)
    starters = role_totals.get("starter", 0)
    handtraps = role_totals.get("handtrap", 0)
    non_starters_non_ht = N - starters - handtraps
    denom5 = comb(N, 5)
    if denom5 > 0 and non_starters_non_ht >= 0:
        dead5 = round(comb(non_starters_non_ht, min(5, non_starters_non_ht)) / denom5, 4)
        denom6 = comb(N, 6)
        dead6 = round(comb(non_starters_non_ht, min(6, non_starters_non_ht)) / denom6, 4) if denom6 > 0 else 0.0
    else:
        dead5 = dead6 = 0.0

    recommendations = _build_recommendations(N, role_totals, dead5, has_roles)

    return ProbabilityOut(
        deck_id=deck.id,
        deck_title=deck.title,
        main_count=N,
        cards=cards,
        groups=groups,
        dead_hand_p5=dead5,
        dead_hand_p6=dead6,
        has_roles=has_roles,
        recommendations=recommendations,
    )


def _build_recommendations(
    N: int,
    role_totals: dict[str, int],
    dead5: float,
    has_roles: bool,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    if not has_roles:
        recs.append(Recommendation(
            level="info",
            text="Taguez vos cartes (starter, extender, handtrap…) pour débloquer les analyses de probabilité.",
        ))
        return recs

    starters = role_totals.get("starter", 0)
    handtraps = role_totals.get("handtrap", 0)
    garnets = role_totals.get("garnet", 0)

    if N < 40:
        recs.append(Recommendation(level="critical", text=f"Main deck trop petit ({N} cartes). Minimum : 40."))
    elif N > 60:
        recs.append(Recommendation(level="warning", text=f"Main deck surdimensionné ({N} cartes). Idéal : 40–42."))

    if starters < 9:
        recs.append(Recommendation(
            level="warning",
            text=f"Seulement {starters} starters. Recommandé : 9–15 pour une main cohérente (≥80% d'en voir un en 5 cartes).",
        ))
    elif starters > 18:
        recs.append(Recommendation(
            level="info",
            text=f"{starters} starters : risque de mains trop «briques» (trop de cartes identiques).",
        ))

    if handtraps < 6:
        recs.append(Recommendation(
            level="warning",
            text=f"Seulement {handtraps} handtraps. Recommandé : 6–12 en méta compétitive.",
        ))

    if garnets > 3:
        recs.append(Recommendation(
            level="warning",
            text=f"{garnets} garnets dans le main — trop de garnets brique une main : gardez ≤ 3.",
        ))

    if dead5 > 0.30:
        recs.append(Recommendation(
            level="critical",
            text=f"Main morte probable à {dead5*100:.1f}% (5 cartes sans starter ni handtrap). Augmentez vos starters ou handtraps.",
        ))
    elif dead5 > 0.15:
        recs.append(Recommendation(
            level="warning",
            text=f"Main morte à {dead5*100:.1f}% — légèrement élevé pour un deck compétitif (cible < 10%).",
        ))
    elif has_roles:
        recs.append(Recommendation(
            level="info",
            text=f"Main morte à {dead5*100:.1f}% — dans la norme compétitive.",
        ))

    return recs
