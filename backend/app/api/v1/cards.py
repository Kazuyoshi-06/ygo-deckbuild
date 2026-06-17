from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Banlist, BanlistEntry, Card, Deck, DeckCard, DeckSubmission
from app.schemas.card import CardDetailOut, CardListOut, CardOut, CurrentBanlistStatus, DeckUsingCardOut
from app.services.image_service import image_service

router = APIRouter(tags=["cards"])


@router.get("", response_model=CardListOut)
async def list_cards(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, description="Search by name (case-insensitive)"),
    archetype: str | None = Query(default=None),
    type: str | None = Query(default=None),
    attribute: str | None = Query(default=None),
    race: str | None = Query(default=None, description="Monster race, e.g. Warrior, Dragon, Spellcaster"),
    level_min: int | None = Query(default=None, description="Min Level/Rank/Link"),
    level_max: int | None = Query(default=None, description="Max Level/Rank/Link"),
    atk_min: int | None = Query(default=None),
    atk_max: int | None = Query(default=None),
    def_min: int | None = Query(default=None),
    def_max: int | None = Query(default=None),
    format: str | None = Query(default=None, description="TCG | OCG | OCG_ONLY"),
    sort: str | None = Query(default=None, description="ocg_newest | name_desc | price_asc | price_desc"),
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
    if race:
        base_q = base_q.where(Card.race == race)
    if level_min is not None:
        base_q = base_q.where(Card.level_rank_link >= level_min)
    if level_max is not None:
        base_q = base_q.where(Card.level_rank_link <= level_max)
    if atk_min is not None:
        base_q = base_q.where(Card.atk >= atk_min)
    if atk_max is not None:
        base_q = base_q.where(Card.atk <= atk_max)
    if def_min is not None:
        base_q = base_q.where(Card.def_ >= def_min)
    if def_max is not None:
        base_q = base_q.where(Card.def_ <= def_max)
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
    elif sort == "price_asc":
        order = [nulls_last(Card.cardmarket_price.asc()), Card.name]
    elif sort == "price_desc":
        order = [nulls_last(Card.cardmarket_price.desc()), Card.name]
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


@router.get("/{card_id}", response_model=CardDetailOut)
async def get_card(card_id: int, db: AsyncSession = Depends(get_db)) -> CardDetailOut:
    card = await db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    status = CurrentBanlistStatus()
    for fmt, attr in (("TCG", "tcg"), ("OCG", "ocg")):
        latest_banlist = await db.scalar(
            select(Banlist).where(Banlist.format == fmt).order_by(Banlist.created_at.desc()).limit(1)
        )
        if latest_banlist:
            entry = await db.scalar(
                select(BanlistEntry).where(
                    BanlistEntry.banlist_id == latest_banlist.id,
                    BanlistEntry.card_id == card_id,
                )
            )
            if entry:
                setattr(status, attr, entry.status.value)

    decks_using_total = (
        await db.scalar(
            select(func.count(func.distinct(Deck.id)))
            .select_from(Deck)
            .join(DeckSubmission, DeckSubmission.deck_id == Deck.id)
            .join(DeckCard, DeckCard.deck_submission_id == DeckSubmission.id)
            .where(DeckCard.card_id == card_id)
        )
        or 0
    )

    deck_rows = await db.execute(
        select(Deck.id, Deck.title, Deck.archetype_label, Deck.updated_at)
        .join(DeckSubmission, DeckSubmission.deck_id == Deck.id)
        .join(DeckCard, DeckCard.deck_submission_id == DeckSubmission.id)
        .where(DeckCard.card_id == card_id)
        .distinct()
        .order_by(Deck.updated_at.desc())
        .limit(20)
    )
    decks_using = [
        DeckUsingCardOut(deck_id=row.id, title=row.title, archetype_label=row.archetype_label)
        for row in deck_rows.all()
    ]

    return CardDetailOut(
        **CardOut.model_validate(card).model_dump(exclude={"image_url"}),
        pend_description=card.pend_description,
        monster_description=card.monster_description,
        current_banlist_status=status,
        decks_using=decks_using,
        decks_using_total=decks_using_total,
    )
