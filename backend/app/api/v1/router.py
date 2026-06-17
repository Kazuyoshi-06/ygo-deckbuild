from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.tournaments import router as tournaments_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.banlists import router as banlists_router
from app.api.v1.cards import router as cards_router
from app.api.v1.compare import router as compare_router
from app.api.v1.decks import router as decks_router
from app.api.v1.probability import router as probability_router
from app.api.v1.ratio_advice import router as ratio_advice_router
from app.api.v1.search import router as search_router
from app.api.v1.score import router as score_router
from app.api.v1.matchup import analytics_router as matchup_analytics_router
from app.api.v1.matchup import router as matchup_router
from app.api.v1.side_optimizer import router as side_optimizer_router
from app.api.v1.simulation import router as simulation_router
from app.api.v1.tournament_prep import router as tournament_prep_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(analytics_router, prefix="/analytics")
router.include_router(matchup_analytics_router, prefix="/analytics")
router.include_router(banlists_router, prefix="/banlists")
router.include_router(cards_router, prefix="/cards")
router.include_router(compare_router, prefix="/compare")
router.include_router(decks_router, prefix="/decks")
router.include_router(probability_router, prefix="/decks")
router.include_router(ratio_advice_router, prefix="/decks")
router.include_router(score_router, prefix="/decks")
router.include_router(matchup_router, prefix="/decks")
router.include_router(side_optimizer_router, prefix="/decks")
router.include_router(simulation_router, prefix="/decks")
router.include_router(tournament_prep_router, prefix="/decks")
router.include_router(search_router, prefix="/search")
router.include_router(tournaments_router, prefix="/tournaments")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "v1"}
