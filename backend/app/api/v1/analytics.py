from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analytics import (
    ArchetypeAnalyticsOut,
    ArchetypeCompareOut,
    DeckAnalyticsOut,
    MetaWinShareOut,
    OcgToTcgPipelineOut,
    OverviewOut,
    TechSuggestionsOut,
    TrendingArchetypesOut,
)
from app.schemas.evolution import EvolutionOut
from app.services import analytics_service, cache_service

router = APIRouter(tags=["analytics"])


@router.get("/overview", response_model=OverviewOut)
async def overview(db: AsyncSession = Depends(get_db)) -> OverviewOut:
    return await analytics_service.get_overview(db)


@router.get("/meta-vs-win-share", response_model=MetaWinShareOut)
async def meta_vs_win_share(db: AsyncSession = Depends(get_db)) -> MetaWinShareOut:
    """Meta share (presence across all placed submissions) vs win share (presence in top 8), per archetype."""
    return await analytics_service.get_meta_vs_win_share(db)


@router.get("/trending", response_model=TrendingArchetypesOut)
async def trending_archetypes(
    weeks: int = Query(default=6, ge=3, le=16, description="Weeks of history to analyze"),
    limit: int = Query(default=5, ge=1, le=10, description="Max entries per rising/falling list"),
    db: AsyncSession = Depends(get_db),
) -> TrendingArchetypesOut:
    """Archetypes rising/falling in meta share over recent weeks — same slope logic as D5's evolution."""
    return await analytics_service.get_trending_archetypes(db, weeks=weeks, limit=limit)


@router.get("/ocg-tcg-pipeline", response_model=OcgToTcgPipelineOut)
async def ocg_tcg_pipeline(
    min_cards: int = Query(default=3, ge=1, le=20, description="Min cards required to count as an archetype"),
    db: AsyncSession = Depends(get_db),
) -> OcgToTcgPipelineOut:
    """OCG-exclusive archetypes with a predicted TCG arrival, based on the historical average release gap."""
    return await analytics_service.get_ocg_to_tcg_pipeline(db, min_cards=min_cards)


@router.get("/decks/{deck_id}", response_model=DeckAnalyticsOut)
async def deck_analytics(deck_id: int, db: AsyncSession = Depends(get_db)) -> DeckAnalyticsOut:
    result = await analytics_service.get_deck_analytics(deck_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return result


@router.get("/archetypes/{archetype_label}", response_model=ArchetypeAnalyticsOut)
async def archetype_analytics(
    archetype_label: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ArchetypeAnalyticsOut | Response:
    """Cached for 5 minutes (T3.7) — invalidated whenever a deck is imported."""
    cached = await cache_service.get_cached(request)
    if cached is not None:
        return Response(content=cached, media_type="application/json")

    result = await analytics_service.get_archetype_analytics(archetype_label, db)
    if result is None:
        raise HTTPException(status_code=404, detail="No decks found for this archetype")
    await cache_service.set_cached(request, result.model_dump_json())
    return result


@router.get("/archetypes/{archetype_label}/tech-suggestions", response_model=TechSuggestionsOut)
async def archetype_tech_suggestions(
    archetype_label: str,
    limit: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> TechSuggestionsOut:
    """Most-played tech cards (frequency < 25%) for an archetype — used by the builder's suggestion panel."""
    result = await analytics_service.get_archetype_tech_suggestions(archetype_label, db, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="No decks found for this archetype")
    return result


@router.get("/archetypes/{archetype_label}/evolution", response_model=EvolutionOut)
async def archetype_evolution(
    archetype_label: str,
    months: int = Query(default=12, ge=2, le=24, description="Number of months to look back"),
    db: AsyncSession = Depends(get_db),
) -> EvolutionOut:
    """Monthly card-presence evolution for an archetype."""
    return await analytics_service.get_archetype_evolution(archetype_label, months, db)


@router.get("/compare", response_model=ArchetypeCompareOut)
async def compare_archetypes(
    archetypes: str = Query(..., description="Comma-separated archetype labels, e.g. 'Kashtira,Branded'"),
    months: int = Query(default=12, ge=2, le=24, description="Months of evolution history per archetype"),
    db: AsyncSession = Depends(get_db),
) -> ArchetypeCompareOut:
    """Side-by-side comparison of 2-4 archetypes: meta share, common/exclusive cards, evolution."""
    labels = [label.strip() for label in archetypes.split(",") if label.strip()]
    labels = list(dict.fromkeys(labels))  # de-duplicate, preserve order

    if len(labels) < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 distinct archetype labels")
    if len(labels) > 4:
        raise HTTPException(status_code=422, detail="Cannot compare more than 4 archetypes at once")

    result = await analytics_service.get_archetype_comparison(labels, db, months=months)
    if result is None:
        raise HTTPException(status_code=404, detail="No decks found for one or more of these archetypes")
    return result
