import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1.router import router as v1_router
from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import configure_logging
from app.services.card_cdb_service import card_cdb_service

configure_logging(settings.environment)
logger = logging.getLogger(__name__)


def _resolve_cdb_sources() -> list[str]:
    """Return the list of CDB sources from config. YGOPRO_CDB_PATHS takes priority."""
    if settings.ygopro_cdb_paths.strip():
        return [p.strip() for p in settings.ygopro_cdb_paths.split(";") if p.strip()]
    if settings.ygopro_cdb_url.strip():
        return [settings.ygopro_cdb_url.strip()]
    return []


async def _startup_cdb_sync(sources: list[str]) -> None:
    """Run a CDB sync in background at startup. Opens its own DB session."""
    logger.info("Auto CDB sync on startup: %d source(s)", len(sources))
    try:
        async with AsyncSessionLocal() as db:
            sync_run = await card_cdb_service.trigger(db)
        await card_cdb_service.execute(sync_run.id, sources)
        logger.info("Auto CDB sync completed (run_id=%s)", sync_run.id)
    except Exception:
        logger.exception("Auto CDB sync on startup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_sync_cdb_on_startup:
        sources = _resolve_cdb_sources()
        if sources:
            asyncio.create_task(_startup_cdb_sync(sources))
        else:
            logger.warning(
                "AUTO_SYNC_CDB_ON_STARTUP=true but no CDB sources configured. "
                "Set YGOPRO_CDB_PATHS (semicolon-separated) or YGOPRO_CDB_URL."
            )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")

# Serve locally cached card images and placeholders at /media
_media_dir = (
    Path(settings.storage_local_path)
    if Path(settings.storage_local_path).is_absolute()
    else Path.cwd() / settings.storage_local_path
)
_media_dir.mkdir(parents=True, exist_ok=True)
(_media_dir / "cards").mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
