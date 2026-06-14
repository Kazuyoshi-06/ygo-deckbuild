from datetime import datetime
from typing import Callable

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import SyncRun
from app.models.enums import SyncStatus
from app.schemas.sync import SyncRunOut
from app.services.banlist_sync_service import banlist_sync_service
from app.services.card_cdb_service import card_cdb_service
from app.services.card_sync import card_sync_service
from app.workers.jobs import run_banlist_sync, run_card_sync, run_cdb_sync
from app.workers.queue import get_queue

router = APIRouter(prefix="/admin", tags=["admin"])

_JOB_TIMEOUT = 3600  # 1 hour max per sync job


async def _enqueue(db: AsyncSession, sync_run: SyncRun, fn: Callable, *args: object) -> None:
    """Enqueue a sync job to RQ. Marks the run as failed if Redis is unreachable."""
    try:
        get_queue().enqueue(fn, *args, job_timeout=_JOB_TIMEOUT)
    except Exception as exc:
        sync_run.status = SyncStatus.failed
        sync_run.finished_at = datetime.utcnow()
        sync_run.error_log = f"Redis unavailable: {exc}"
        await db.commit()
        raise HTTPException(
            status_code=503,
            detail="Job queue unavailable. Make sure Redis is running, then start the worker with: python start_worker.py",
        )


@router.post("/sync/cards", status_code=202, response_model=SyncRunOut)
async def trigger_card_sync(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SyncRun:
    """Enqueue a full card catalog sync from YGOProDeck."""
    sync_run = await card_sync_service.trigger(db)
    await _enqueue(db, sync_run, run_card_sync, sync_run.id)
    return sync_run


@router.post("/sync/cards/cdb", status_code=202, response_model=SyncRunOut)
async def trigger_cdb_sync(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
    sources: list[str] = Body(
        default=[],
        description=(
            "List of local paths to .cdb files (EdoPro format). "
            "Pass the base cards.cdb plus any delta/prerelease files you want merged. "
            "If empty, falls back to YGOPRO_CDB_URL from config (single file)."
        ),
    ),
) -> SyncRun:
    """Enqueue a CDB sync from EdoPro/YGOPRO .cdb files."""
    resolved = [s.strip() for s in sources if s.strip()]
    if not resolved:
        fallback = settings.ygopro_cdb_url.strip()
        if not fallback:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No CDB sources provided. "
                    "Pass a list of file paths in the request body, "
                    "or set YGOPRO_CDB_URL in .env"
                ),
            )
        resolved = [fallback]

    sync_run = await card_cdb_service.trigger(db)
    await _enqueue(db, sync_run, run_cdb_sync, sync_run.id, resolved)
    return sync_run


@router.post("/sync/banlist", status_code=202, response_model=SyncRunOut)
async def trigger_banlist_sync(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SyncRun:
    """Enqueue a banlist sync from YGOProDeck (TCG + OCG)."""
    sync_run = await banlist_sync_service.trigger(db)
    await _enqueue(db, sync_run, run_banlist_sync, sync_run.id)
    return sync_run


@router.get("/sync/runs", response_model=list[SyncRunOut])
async def list_sync_runs(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[SyncRun]:
    """List recent sync runs, most recent first."""
    result = await db.execute(
        select(SyncRun).order_by(SyncRun.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/sync/runs/{run_id}", response_model=SyncRunOut)
async def get_sync_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> SyncRun:
    """Get a specific sync run by ID."""
    run = await db.get(SyncRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")
    return run
