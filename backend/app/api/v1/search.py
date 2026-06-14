from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Card, Deck
from app.schemas.search import ArchetypeHit, CardHit, DeckHit, SearchOut

router = APIRouter(tags=["search"])

_LIMIT = 5


def _type_label(card_type: str) -> str:
    t = card_type.lower()
    if "monster" in t:
        return "Monster"
    if "spell" in t:
        return "Spell"
    if "trap" in t:
        return "Trap"
    return "Other"


@router.get("", response_model=SearchOut)
async def search(
    q: str = Query(..., min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> SearchOut:
    pattern = f"%{q}%"

    card_rows = await db.execute(
        select(Card).where(Card.name.ilike(pattern)).order_by(Card.name).limit(_LIMIT)
    )
    cards = [
        CardHit(
            id=c.id,
            name=c.name,
            type_label=_type_label(c.type),
            image_url=f"/api/v1/cards/{c.id}/image",
        )
        for c in card_rows.scalars()
    ]

    deck_rows = await db.execute(
        select(Deck).where(Deck.title.ilike(pattern)).order_by(Deck.title).limit(_LIMIT)
    )
    decks = [
        DeckHit(id=d.id, title=d.title, archetype_label=d.archetype_label)
        for d in deck_rows.scalars()
    ]

    arch_rows = await db.execute(
        select(Deck.archetype_label, func.count(Deck.id).label("cnt"))
        .where(Deck.archetype_label.isnot(None))
        .where(Deck.archetype_label.ilike(pattern))
        .group_by(Deck.archetype_label)
        .order_by(func.count(Deck.id).desc())
        .limit(_LIMIT)
    )
    archetypes = [
        ArchetypeHit(label=row.archetype_label, deck_count=row.cnt)
        for row in arch_rows.all()
        if row.archetype_label
    ]

    return SearchOut(cards=cards, decks=decks, archetypes=archetypes)
