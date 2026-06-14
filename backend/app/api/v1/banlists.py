from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.banlist import Banlist, BanlistEntry
from app.models.enums import BanlistStatus
from app.schemas.banlist import (
    BanlistDetailOut,
    BanlistEntryOut,
    BanlistSummaryOut,
    LatestBanlistsOut,
)

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
