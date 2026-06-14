from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Card
from app.schemas.card import CardListOut, CardOut
from app.services.image_service import image_service

router = APIRouter(tags=["cards"])


@router.get("", response_model=CardListOut)
async def list_cards(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, description="Search by name (case-insensitive)"),
    archetype: str | None = Query(default=None),
    type: str | None = Query(default=None),
    attribute: str | None = Query(default=None),
    format: str | None = Query(default=None, description="TCG | OCG | OCG_ONLY"),
    sort: str | None = Query(default=None, description="ocg_newest | name_desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=40, ge=1, le=200),
) -> CardListOut:
    base_q = select(Card)

    if q:
        base_q = base_q.where(Card.name.ilike(f"%{q}%"))
    if archetype:
        base_q = base_q.where(Card.archetype.ilike(f"%{archetype}%"))
    if type:
        base_q = base_q.where(Card.type.ilike(f"%{type}%"))
    if attribute:
        base_q = base_q.where(Card.attribute == attribute.upper())
    if format == "TCG":
        base_q = base_q.where(Card.tcg_date.isnot(None))
    elif format == "OCG":
        base_q = base_q.where(Card.ocg_date.isnot(None))
    elif format == "OCG_ONLY":
        base_q = base_q.where(Card.ocg_date.isnot(None)).where(Card.tcg_date.is_(None))

    total_result = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = total_result.scalar() or 0

    if sort == "ocg_newest":
        order = [nulls_last(Card.ocg_date.desc()), Card.name]
    elif sort == "name_desc":
        order = [Card.name.desc()]
    else:
        order = [Card.name]

    offset = (page - 1) * limit
    result = await db.execute(base_q.order_by(*order).offset(offset).limit(limit))
    items = list(result.scalars().all())

    return CardListOut(items=items, total=total, page=page, limit=limit)


@router.get("/{card_id}/image")
async def get_card_image(
    card_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Return the card image. Redirects to local cache if ready; queues download otherwise."""
    card = await db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    url = await image_service.get_image_url(card, db, background_tasks)
    return RedirectResponse(url=url, status_code=302)


@router.get("/{card_id}", response_model=CardOut)
async def get_card(card_id: int, db: AsyncSession = Depends(get_db)) -> Card:
    card = await db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card
