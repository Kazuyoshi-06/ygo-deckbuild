import logging
import time
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Card, SyncRun
from app.models.banlist import Banlist, BanlistEntry
from app.models.enums import BanlistStatus, SyncStatus, SyncType
from app.monitoring import record_sync_result, send_alert_webhook
from app.services.ygopro_client import ygopro_client

logger = logging.getLogger(__name__)

_BAN_MAP: dict[str, tuple[BanlistStatus, int]] = {
    "Forbidden": (BanlistStatus.forbidden, 0),
    "Limited": (BanlistStatus.limited, 1),
    "Semi-Limited": (BanlistStatus.semi_limited, 2),
}

_FORMATS = [("TCG", "ban_tcg"), ("OCG", "ban_ocg")]


class BanlistSyncService:
    async def trigger(self, db: AsyncSession) -> SyncRun:
        running = await db.scalar(
            select(SyncRun).where(
                SyncRun.sync_type == SyncType.banlist,
                SyncRun.status == SyncStatus.running,
            )
        )
        if running:
            return running
        sync_run = SyncRun(sync_type=SyncType.banlist, status=SyncStatus.running)
        db.add(sync_run)
        await db.commit()
        await db.refresh(sync_run)
        return sync_run

    async def execute(self, sync_run_id: int) -> None:
        async with AsyncSessionLocal() as db:
            sync_run = await db.get(SyncRun, sync_run_id)
            if not sync_run:
                return
            start = time.monotonic()
            try:
                await self._do_sync(db, sync_run)
                record_sync_result("banlist", "success", time.monotonic() - start)
            except Exception as exc:
                elapsed = time.monotonic() - start
                logger.exception("Banlist sync failed")
                record_sync_result("banlist", "failed", elapsed)
                await send_alert_webhook("banlist", str(exc), sync_run_id)
                sync_run.status = SyncStatus.failed
                sync_run.finished_at = datetime.utcnow()
                sync_run.error_log = str(exc)
                try:
                    await db.commit()
                except Exception:
                    pass

    async def _do_sync(self, db: AsyncSession, sync_run: SyncRun) -> None:
        logger.info("Banlist sync: fetching card data from YGOProDeck...")
        raw_cards = await ygopro_client.fetch_all_cards()

        # Extract ban info per format: {external_card_id: (status, limit_value)}
        ban_data: dict[str, dict[int, tuple[BanlistStatus, int]]] = {"TCG": {}, "OCG": {}}
        relevant_ids: set[int] = set()

        for raw in raw_cards:
            ban_info = raw.get("banlist_info") or {}
            for fmt, ban_key in _FORMATS:
                ban_val = ban_info.get(ban_key)
                if ban_val and ban_val in _BAN_MAP:
                    ban_data[fmt][raw["id"]] = _BAN_MAP[ban_val]
                    relevant_ids.add(raw["id"])

        # Bulk load card DB IDs for all cards that appear in any banlist
        ext_to_db_id: dict[int, int] = {}
        if relevant_ids:
            rows = await db.execute(
                select(Card.external_card_id, Card.id).where(
                    Card.external_card_id.in_(relevant_ids)
                )
            )
            ext_to_db_id = {ext: db_id for ext, db_id in rows}

        today = date.today()
        total_entries = 0
        created_banlists = []

        for fmt, _ in _FORMATS:
            entries = ban_data[fmt]

            # Build fingerprint of incoming data: frozenset of (db_card_id, status_value)
            incoming: dict[int, tuple[BanlistStatus, int]] = {}
            for ext_id, (status, limit_val) in entries.items():
                db_id = ext_to_db_id.get(ext_id)
                if db_id is not None:
                    incoming[db_id] = (status, limit_val)

            incoming_fp = frozenset((db_id, st.value) for db_id, (st, _) in incoming.items())

            # Compare with the latest existing banlist for this format
            latest_bl = await db.scalar(
                select(Banlist)
                .where(Banlist.format == fmt)
                .order_by(Banlist.created_at.desc())
                .limit(1)
            )
            if latest_bl is not None:
                existing_rows = await db.execute(
                    select(BanlistEntry.card_id, BanlistEntry.status)
                    .where(BanlistEntry.banlist_id == latest_bl.id)
                )
                existing_fp = frozenset((cid, st.value) for cid, st in existing_rows)
                if existing_fp == incoming_fp:
                    logger.info(f"Banlist {fmt}: no changes since last sync — skipping new record")
                    created_banlists.append({"format": fmt, "banlist_id": latest_bl.id, "entries": len(incoming), "skipped": True})
                    continue

            banlist = Banlist(
                format=fmt,
                source_name="YGOProDeck API",
                source_url="https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes",
                effective_date=today,
                version_label=f"{fmt} {today.isoformat()}",
            )
            db.add(banlist)
            await db.flush()

            for db_id, (status, limit_val) in incoming.items():
                db.add(BanlistEntry(
                    banlist_id=banlist.id,
                    card_id=db_id,
                    status=status,
                    limit_value=limit_val,
                ))
                total_entries += 1

            await db.commit()
            created_banlists.append({"format": fmt, "banlist_id": banlist.id, "entries": len(incoming)})
            logger.info(f"Banlist {fmt} created: id={banlist.id}, {len(incoming)} entries")

        sync_run.status = SyncStatus.completed
        sync_run.finished_at = datetime.utcnow()
        sync_run.summary_json = {"banlists": created_banlists, "total_entries": total_entries}
        await db.commit()
        logger.info(f"Banlist sync completed: {total_entries} total entries across {len(_FORMATS)} formats")


banlist_sync_service = BanlistSyncService()
