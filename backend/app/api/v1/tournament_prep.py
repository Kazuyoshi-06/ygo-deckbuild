from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.tournament_prep import TournamentPrepOut
from app.services.tournament_prep_service import get_tournament_prep

router = APIRouter(tags=["tournament-prep"])


@router.get("/{deck_id}/tournament-prep", response_model=TournamentPrepOut)
async def tournament_prep(
    deck_id: int,
    top_n: int = Query(default=3, ge=1, le=8, description="Number of top archetypes to prep against"),
    db: AsyncSession = Depends(get_db),
) -> TournamentPrepOut:
    """Pre-tournament briefing: expected meta, weighted side recommendations, banlist legality."""
    result = await get_tournament_prep(deck_id, db, top_n=top_n)
    if result is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return result
