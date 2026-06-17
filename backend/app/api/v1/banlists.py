from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.banlist import Banlist, BanlistEntry
from app.models.enums import BanlistStatus
from app.schemas.banlist import (
    BanlistCardHistoryEntry,
    BanlistDetailOut,
    BanlistDiffEntry,
    BanlistDiffOut,
    BanlistEntryOut,
    BanlistPredictionOut,
    BanlistSummaryOut,
    CardReplacementsOut,
    LatestBanlistsOut,
)
from app.services.banlist_prediction_service import get_banlist_prediction
from app.services.replacement_service import get_card_replacements

_SEVERITY: dict[BanlistStatus | None, int] = {
    BanlistStatus.forbidden: 3,
    BanlistStatus.limited: 2,
    BanlistStatus.semi_limited: 1,
    None: 0,
}

router = APIRouter(tags=["banlists"])


async def _banlist_summary(db: AsyncSession, banlist: Banlist) -> BanlistSummaryOut:
    counts = await db.execute(
        select(BanlistEntry.status, func.count(BanlistEntry.id))
        .where(BanlistEntry.banlist_id == banlist.id)
        .group_by(BanlistEntry.status)
    )
    count_map = {row[0]: row[1] for row in counts}
    return BanlistSummaryOut(
        id=banlist.id,
        format=banlist.format,
        effective_date=banlist.effective_date,
        version_label=banlist.version_label,
        forbidden_count=count_map.get(BanlistStatus.forbidden, 0),
        limited_count=count_map.get(BanlistStatus.limited, 0),
        semi_limited_count=count_map.get(BanlistStatus.semi_limited, 0),
    )


def _entry_to_out(entry: BanlistEntry) -> BanlistEntryOut:
    card = entry.card
    return BanlistEntryOut(
        card_id=card.id,
        external_card_id=card.external_card_id,
        name=card.name,
        image_url=f"/api/v1/cards/{card.id}/image",
        status=entry.status.value,
        limit_value=entry.limit_value,
    )


@router.get("/latest", response_model=LatestBanlistsOut)
async def get_latest_banlists(db: AsyncSession = Depends(get_db)) -> LatestBanlistsOut:
    result: dict = {}
    for fmt, key in [("TCG", "tcg"), ("OCG", "ocg")]:
        row = await db.scalar(
            select(Banlist)
            .where(Banlist.format == fmt)
            .order_by(Banlist.created_at.desc())
            .limit(1)
        )
        if row:
            result[key] = await _banlist_summary(db, row)
    return LatestBanlistsOut(**result)


@router.get("", response_model=list[BanlistSummaryOut])
async def list_banlists(db: AsyncSession = Depends(get_db)) -> list[BanlistSummaryOut]:
    rows = await db.execute(
        select(Banlist).order_by(Banlist.created_at.desc()).limit(50)
    )
    return [await _banlist_summary(db, b) for b in rows.scalars()]


@router.get("/diff", response_model=BanlistDiffOut)
async def get_banlist_diff(
    from_id: int = Query(...),
    to_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> BanlistDiffOut:
    from_bl = await db.scalar(select(Banlist).where(Banlist.id == from_id))
    to_bl = await db.scalar(select(Banlist).where(Banlist.id == to_id))
    if not from_bl or not to_bl:
        raise HTTPException(status_code=404, detail="Banlist not found")

    from_result = await db.execute(
        select(BanlistEntry)
        .where(BanlistEntry.banlist_id == from_id)
        .options(selectinload(BanlistEntry.card))
    )
    to_result = await db.execute(
        select(BanlistEntry)
        .where(BanlistEntry.banlist_id == to_id)
        .options(selectinload(BanlistEntry.card))
    )

    from_map: dict[int, BanlistEntry] = {e.card_id: e for e in from_result.scalars()}
    to_map: dict[int, BanlistEntry] = {e.card_id: e for e in to_result.scalars()}
    all_ids = set(from_map) | set(to_map)

    hits: list[BanlistDiffEntry] = []
    shifts: list[BanlistDiffEntry] = []
    frees: list[BanlistDiffEntry] = []

    for cid in sorted(all_ids):
        from_entry = from_map.get(cid)
        to_entry = to_map.get(cid)

        from_status = from_entry.status if from_entry else None
        to_status = to_entry.status if to_entry else None

        if from_status == to_status:
            continue

        from_sev = _SEVERITY[from_status]
        to_sev = _SEVERITY[to_status]

        card = (to_entry or from_entry).card  # type: ignore[union-attr]
        entry = BanlistDiffEntry(
            card_id=card.id,
            external_card_id=card.external_card_id,
            name=card.name,
            image_url=f"/api/v1/cards/{card.id}/image",
            from_status=from_status.value if from_status else None,
            to_status=to_status.value if to_status else None,
        )

        if to_sev > from_sev:
            hits.append(entry)
        elif to_sev == 0:
            frees.append(entry)
        else:
            shifts.append(entry)

    hits.sort(key=lambda x: x.name)
    shifts.sort(key=lambda x: x.name)
    frees.sort(key=lambda x: x.name)

    return BanlistDiffOut(
        from_banlist=await _banlist_summary(db, from_bl),
        to_banlist=await _banlist_summary(db, to_bl),
        hits=hits,
        shifts=shifts,
        frees=frees,
    )


@router.get("/cards/{card_id}/history", response_model=list[BanlistCardHistoryEntry])
async def get_card_banlist_history(
    card_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[BanlistCardHistoryEntry]:
    result = await db.execute(
        select(BanlistEntry, Banlist)
        .join(Banlist, BanlistEntry.banlist_id == Banlist.id)
        .where(BanlistEntry.card_id == card_id)
        .order_by(Banlist.effective_date.desc())
    )
    return [
        BanlistCardHistoryEntry(
            banlist_id=bl.id,
            format=bl.format,
            effective_date=bl.effective_date,
            version_label=bl.version_label,
            status=entry.status.value,
        )
        for entry, bl in result.all()
    ]


@router.get("/cards/{card_id}/replacements", response_model=CardReplacementsOut)
async def card_replacements(
    card_id: int,
    format: str = Query(default="TCG", description="TCG | OCG"),
    db: AsyncSession = Depends(get_db),
) -> CardReplacementsOut:
    """For a currently-forbidden card, find cards that replaced it in affected archetypes after the ban."""
    result = await get_card_replacements(card_id, format.upper(), db)
    if result is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return result


@router.get("/prediction", response_model=BanlistPredictionOut)
async def banlist_prediction(
    format: str = Query(default="TCG", description="TCG | OCG"),
    db: AsyncSession = Depends(get_db),
) -> BanlistPredictionOut:
    """Heuristic banlist-risk score for currently-unrestricted cards. Not an official prediction."""
    return await get_banlist_prediction(db, format.upper())


@router.get("/{banlist_id}", response_model=BanlistDetailOut)
async def get_banlist(banlist_id: int, db: AsyncSession = Depends(get_db)) -> BanlistDetailOut:
    banlist = await db.scalar(
        select(Banlist)
        .where(Banlist.id == banlist_id)
        .options(selectinload(Banlist.entries).selectinload(BanlistEntry.card))
    )
    if not banlist:
        raise HTTPException(status_code=404, detail="Banlist not found")

    forbidden: list[BanlistEntryOut] = []
    limited: list[BanlistEntryOut] = []
    semi_limited: list[BanlistEntryOut] = []

    for entry in banlist.entries:
        out = _entry_to_out(entry)
        if entry.status == BanlistStatus.forbidden:
            forbidden.append(out)
        elif entry.status == BanlistStatus.limited:
            limited.append(out)
        else:
            semi_limited.append(out)

    forbidden.sort(key=lambda x: x.name)
    limited.sort(key=lambda x: x.name)
    semi_limited.sort(key=lambda x: x.name)

    return BanlistDetailOut(
        id=banlist.id,
        format=banlist.format,
        effective_date=banlist.effective_date,
        version_label=banlist.version_label,
        forbidden=forbidden,
        limited=limited,
        semi_limited=semi_limited,
    )
