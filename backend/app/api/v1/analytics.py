from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analytics import ArchetypeAnalyticsOut, DeckAnalyticsOut, OverviewOut
from app.services import analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/overview", response_model=OverviewOut)
async def overview(db: AsyncSession = Depends(get_db)) -> OverviewOut:
    return await analytics_service.get_overview(db)


@router.get("/decks/{deck_id}", response_model=DeckAnalyticsOut)
async def deck_analytics(deck_id: int, db: AsyncSession = Depends(get_db)) -> DeckAnalyticsOut:
    result = await analytics_service.get_deck_analytics(deck_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return result


@router.get("/archetypes/{archetype_label}", response_model=ArchetypeAnalyticsOut)
async def archetype_analytics(
    archetype_label: str,
    db: AsyncSession = Depends(get_db),
) -> ArchetypeAnalyticsOut:
    result = await analytics_service.get_archetype_analytics(archetype_label, db)
    if result is None:
        raise HTTPException(status_code=404, detail="No decks found for this archetype")
    return result
