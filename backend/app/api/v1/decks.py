from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.dependencies import get_current_user
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Card, Deck, DeckCard, DeckSubmission
from app.models.banlist import Banlist, BanlistEntry
from app.models.enums import CardSection
from app.schemas.banlist import DeckLegalityOut, LegalityViolation, RestrictedCard
from app.schemas.deck import (
    DeckCardOut,
    DeckCreateIn,
    DeckDetailOut,
    DeckImportOut,
    DeckListOut,
    DeckUpdateIn,
)
from app.services.deck_import_service import deck_import_service
from app.services.ydk_parser import parse as parse_ydk

router = APIRouter(tags=["decks"])

_MAX_UPLOAD_BYTES = 512 * 1024


@router.post("/import/ydk", response_model=DeckImportOut, status_code=201)
async def import_ydk(
    file: UploadFile = File(..., description=".ydk deck file"),
    title: str | None = Form(default=None, description="Deck name (defaults to filename)"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> DeckImportOut:
    """Import a deck from a .ydk file."""
    filename = file.filename or ""
    if not filename.lower().endswith(".ydk"):
        raise HTTPException(status_code=422, detail="File must have a .ydk extension")

    raw = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 512 KB)")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    parsed = parse_ydk(text)
    if parsed.is_empty:
        raise HTTPException(status_code=422, detail="YDK file contains no card IDs")

    deck_title = (title or "").strip() or filename.removesuffix(".ydk") or "Imported Deck"
    return await deck_import_service.import_ydk(db, parsed, deck_title)


@router.post("/manual", response_model=DeckImportOut, status_code=201)
async def create_manual_deck(
    data: DeckCreateIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> DeckImportOut:
    """Create a deck manually from a list of card IDs."""
    return await deck_import_service.create_manual(db, data)


@router.delete("", status_code=204)
async def delete_all_decks(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    """Delete every deck (and all their submissions and cards)."""
    all_decks = await db.execute(select(Deck))
    for deck in all_decks.scalars():
        await db.delete(deck)
    await db.commit()


@router.get("", response_model=DeckListOut)
async def list_decks(
    db: AsyncSession = Depends(get_db),
    tag: str | None = Query(default=None, description="Filter by tag"),
    archetype: str | None = Query(default=None, description="Filter by archetype label"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> DeckListOut:
    base_q = select(Deck)
    if tag:
        base_q = base_q.where(cast(Deck.tags, JSONB).contains([tag]))
    if archetype:
        base_q = base_q.where(Deck.archetype_label == archetype)
    total = await db.scalar(select(func.count()).select_from(base_q.subquery())) or 0
    offset = (page - 1) * limit
    rows = await db.execute(
        base_q.order_by(Deck.updated_at.desc()).offset(offset).limit(limit)
    )
    return DeckListOut(items=list(rows.scalars()), total=total, page=page, limit=limit)


@router.get("/{deck_id}", response_model=DeckDetailOut)
async def get_deck(deck_id: int, db: AsyncSession = Depends(get_db)) -> DeckDetailOut:
    """Return a deck with its cards organised by section."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    submission_row = await db.execute(
        select(DeckSubmission)
        .where(DeckSubmission.deck_id == deck_id)
        .options(selectinload(DeckSubmission.cards).selectinload(DeckCard.card))
        .order_by(DeckSubmission.created_at.desc())
        .limit(1)
    )
    submission = submission_row.scalar_one_or_none()

    main: list[DeckCardOut] = []
    extra: list[DeckCardOut] = []
    side: list[DeckCardOut] = []

    if submission:
        for dc in submission.cards:
            card: Card = dc.card
            entry = DeckCardOut(
                card_id=card.id,
                external_card_id=card.external_card_id,
                name=card.name,
                section=dc.section.value,
                quantity=dc.quantity,
                image_url=f"/api/v1/cards/{card.id}/image",
                tcg_date=card.tcg_date,
                ocg_date=card.ocg_date,
            )
            if dc.section == CardSection.main:
                main.append(entry)
            elif dc.section == CardSection.extra:
                extra.append(entry)
            else:
                side.append(entry)

    main.sort(key=lambda c: c.name)
    extra.sort(key=lambda c: c.name)
    side.sort(key=lambda c: c.name)

    return DeckDetailOut(
        id=deck.id,
        title=deck.title,
        archetype_label=deck.archetype_label,
        source_type=deck.source_type.value,
        notes=deck.notes,
        tags=deck.tags or [],
        main=main,
        extra=extra,
        side=side,
        main_count=sum(c.quantity for c in main),
        extra_count=sum(c.quantity for c in extra),
        side_count=sum(c.quantity for c in side),
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )


@router.patch("/{deck_id}", response_model=DeckDetailOut)
async def update_deck(
    deck_id: int,
    data: DeckUpdateIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> DeckDetailOut:
    """Update deck metadata (title, archetype_label, notes)."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if data.title is not None:
        deck.title = data.title
    if data.archetype_label is not None:
        deck.archetype_label = data.archetype_label or None
    if data.notes is not None:
        deck.notes = data.notes or None
    if data.tags is not None:
        deck.tags = data.tags or None
    await db.commit()
    await db.refresh(deck)
    return await get_deck(deck_id, db)


@router.delete("/{deck_id}", status_code=204)
async def delete_deck(
    deck_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> None:
    """Delete a deck and all its submissions and cards."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    await db.delete(deck)
    await db.commit()


@router.get("/{deck_id}/legality", response_model=DeckLegalityOut)
async def get_deck_legality(
    deck_id: int,
    format: str = Query(default="TCG"),
    db: AsyncSession = Depends(get_db),
) -> DeckLegalityOut:
    """Check deck conformity against the latest banlist for a format (TCG or OCG)."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    fmt = format.upper()
    banlist = await db.scalar(
        select(Banlist)
        .where(Banlist.format == fmt)
        .order_by(Banlist.created_at.desc())
        .limit(1)
    )

    if not banlist:
        return DeckLegalityOut(deck_id=deck_id, format=fmt, is_legal=True, violations=[])

    submission_row = await db.execute(
        select(DeckSubmission)
        .where(DeckSubmission.deck_id == deck_id)
        .options(selectinload(DeckSubmission.cards).selectinload(DeckCard.card))
        .order_by(DeckSubmission.created_at.desc())
        .limit(1)
    )
    submission = submission_row.scalar_one_or_none()

    if not submission:
        return DeckLegalityOut(deck_id=deck_id, banlist_id=banlist.id, format=fmt, is_legal=True, violations=[])

    # Aggregate total copies per card across all sections
    totals: dict[int, tuple[str, int]] = {}
    for dc in submission.cards:
        cid = dc.card.id
        name = dc.card.name
        _, qty = totals.get(cid, (name, 0))
        totals[cid] = (name, qty + dc.quantity)

    # Fetch ban entries for the cards in this deck
    entries_result = await db.execute(
        select(BanlistEntry).where(
            BanlistEntry.banlist_id == banlist.id,
            BanlistEntry.card_id.in_(list(totals.keys())),
        )
    )
    ban_map: dict[int, BanlistEntry] = {e.card_id: e for e in entries_result.scalars()}

    violations: list[LegalityViolation] = []
    restricted: list[RestrictedCard] = []
    for cid, (name, total_qty) in totals.items():
        entry = ban_map.get(cid)
        if not entry:
            continue
        restricted.append(RestrictedCard(
            card_id=cid,
            name=name,
            status=entry.status.value,
            limit_value=entry.limit_value,
        ))
        if total_qty > entry.limit_value:
            violations.append(LegalityViolation(
                card_id=cid,
                name=name,
                status=entry.status.value,
                limit_value=entry.limit_value,
                actual_quantity=total_qty,
            ))

    violations.sort(key=lambda v: v.name)
    restricted.sort(key=lambda r: r.name)
    return DeckLegalityOut(
        deck_id=deck_id,
        banlist_id=banlist.id,
        format=fmt,
        is_legal=len(violations) == 0,
        violations=violations,
        restricted=restricted,
    )
