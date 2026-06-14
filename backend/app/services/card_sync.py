import logging
import time
from datetime import datetime

from slugify import slugify
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Card, SyncRun
from app.models.enums import SyncStatus, SyncType
from app.monitoring import record_sync_result, send_alert_webhook
from app.services.ygopro_client import ygopro_client

logger = logging.getLogger(__name__)

BATCH_SIZE = 200
_CARD_TABLE = Card.__table__
_UPDATE_EXCLUDE = {"id", "external_card_id", "created_at"}


class CardSyncService:
    async def trigger(self, db: AsyncSession) -> SyncRun:
        """Create a SyncRun record. Returns existing one if already running."""
        running = await db.scalar(
            select(SyncRun).where(
                SyncRun.sync_type == SyncType.cards,
                SyncRun.status == SyncStatus.running,
            )
        )
        if running:
            return running

        sync_run = SyncRun(sync_type=SyncType.cards, status=SyncStatus.running)
        db.add(sync_run)
        await db.commit()
        await db.refresh(sync_run)
        return sync_run

    async def execute(self, sync_run_id: int) -> None:
        """Full sync. Opens its own DB session — safe for RQ workers."""
        async with AsyncSessionLocal() as db:
            sync_run = await db.get(SyncRun, sync_run_id)
            if not sync_run:
                return
            start = time.monotonic()
            try:
                await self._do_sync(db, sync_run)
                record_sync_result("cards", "success", time.monotonic() - start)
            except Exception as exc:
                elapsed = time.monotonic() - start
                logger.exception("Card sync failed")
                record_sync_result("cards", "failed", elapsed)
                await send_alert_webhook("cards", str(exc), sync_run_id)
                sync_run.status = SyncStatus.failed
                sync_run.finished_at = datetime.utcnow()
                sync_run.error_log = str(exc)
                try:
                    await db.commit()
                except Exception:
                    pass

    async def _do_sync(self, db: AsyncSession, sync_run: SyncRun) -> None:
        raw_cards = await ygopro_client.fetch_all_cards()
        total = len(raw_cards)
        logger.info(f"Card sync started: {total} cards to process")

        upserted = 0
        for i in range(0, total, BATCH_SIZE):
            batch = raw_cards[i : i + BATCH_SIZE]
            batch_data = [self._transform_card(raw) for raw in batch]

            # Build update_set fresh per batch so excluded refs are correct
            stmt = pg_insert(_CARD_TABLE).values(batch_data)
            update_set = {
                col.name: stmt.excluded[col.name]
                for col in _CARD_TABLE.columns
                if col.name not in _UPDATE_EXCLUDE
            }
            update_set["updated_at"] = func.now()

            stmt = stmt.on_conflict_do_update(
                index_elements=["external_card_id"],
                set_=update_set,
            )
            await db.execute(stmt)
            await db.commit()

            upserted += len(batch)
            logger.info(f"Card sync progress: {upserted}/{total} ({upserted*100//total}%)")

        sync_run.status = SyncStatus.completed
        sync_run.finished_at = datetime.utcnow()
        sync_run.summary_json = {"total": total, "upserted": upserted}
        await db.commit()
        logger.info(f"Card sync completed: {upserted} cards upserted")

    def _transform_card(self, raw: dict) -> dict:
        name = raw["name"]
        misc = (raw.get("misc_info") or [{}])[0]
        level_or_rank = raw.get("level") or raw.get("rank")

        return {
            "external_card_id": raw["id"],
            "name": name,
            "slug": f"{slugify(name)}-{raw['id']}",
            "type": raw.get("type", "Unknown"),
            "frame_type": raw.get("frameType", "normal"),
            "race": raw.get("race"),
            "attribute": raw.get("attribute"),
            "archetype": raw.get("archetype"),
            "level_rank_link": level_or_rank,
            "atk": raw.get("atk"),
            "def": raw.get("def"),  # SQL column name (reserved word in Python)
            "scale": raw.get("scale"),
            "linkval": raw.get("linkval"),
            "description": raw.get("desc"),
            "pend_description": raw.get("pend_desc"),
            "monster_description": raw.get("monster_desc"),
            "tcg_date": self._parse_date(misc.get("tcg_date")),
            "ocg_date": self._parse_date(misc.get("ocg_date")),
        }

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None


card_sync_service = CardSyncService()
