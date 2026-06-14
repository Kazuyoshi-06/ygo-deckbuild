"""
Sync card data from one or more YGOPRO/EdoPro cards.cdb SQLite files.

EdoPro uses:
  - expansions/cards.cdb          — main database
  - repositories/*/cards.delta.cdb — incremental updates
  - repositories/*/prerelease-*.cdb — pre-release cards (ot=0x101/0x102)
  - repositories/*/release-*.cdb   — recently released sets

Strategy:
 - Merge all provided CDB files by external_card_id (later files win on conflict).
 - Only INSERT cards not already in our DB — never overwrite YGOProDeck-enriched data.
 - Pre-release cards (EdoPro ot & 0x100) are included.
 - Rush Duel (ot & 0x8) and anime/unofficial (ot & 0x4) are skipped.
"""

import asyncio
import logging
import sqlite3
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Card, SyncRun
from app.models.enums import SyncStatus, SyncType
from app.monitoring import record_sync_result, send_alert_webhook
from app.services.cdb_decoder import (
    decode_attribute,
    decode_frame_type,
    decode_level,
    decode_race,
    decode_type_string,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
_CARD_TABLE = Card.__table__
_UNKNOWN_ATK_DEF = -2   # CDB uses -2 for "?" ATK/DEF

# Valid ot values: OCG=1, TCG=2, both=3, plus EdoPro pre-release variants (+0x100)
_VALID_OT = {0x1, 0x2, 0x3, 0x101, 0x102, 0x103}

# Skip Rush Duel (0x8) and anime/unofficial (0x4)
_SKIP_OT_MASK = 0x4 | 0x8


def _is_valid_ot(ot: int) -> bool:
    if ot & _SKIP_OT_MASK:
        return False
    # Strip pre-release bit then check base value is 1, 2, or 3
    base = ot & ~0x100
    return base in {0x1, 0x2, 0x3}


class CardCdbService:
    async def trigger(self, db: AsyncSession) -> SyncRun:
        sync_run = SyncRun(sync_type=SyncType.cdb, status=SyncStatus.running)
        db.add(sync_run)
        await db.commit()
        await db.refresh(sync_run)
        return sync_run

    async def execute(self, sync_run_id: int, sources: list[str]) -> None:
        """Run the CDB sync in background. `sources` is a list of file paths."""
        async with AsyncSessionLocal() as db:
            sync_run = await db.get(SyncRun, sync_run_id)
            if not sync_run:
                return
            start = time.monotonic()
            try:
                await self._do_sync(db, sync_run, sources)
                record_sync_result("cdb", "success", time.monotonic() - start)
            except Exception as exc:
                elapsed = time.monotonic() - start
                logger.exception("CDB sync failed")
                record_sync_result("cdb", "failed", elapsed)
                await send_alert_webhook("cdb", str(exc), sync_run_id)
                sync_run.status = SyncStatus.failed
                sync_run.finished_at = datetime.utcnow()
                sync_run.error_log = str(exc)
                try:
                    await db.commit()
                except Exception:
                    pass

    async def _do_sync(
        self, db: AsyncSession, sync_run: SyncRun, sources: list[str]
    ) -> None:
        # Resolve paths (download URLs if needed)
        paths: list[tuple[Path, bool]] = []   # (path, is_temp)
        for src in sources:
            if src.startswith("http://") or src.startswith("https://"):
                p = await self._download(src)
                paths.append((p, True))
            else:
                paths.append((Path(src), False))

        try:
            # Collect IDs already in DB
            existing_result = await db.execute(select(Card.external_card_id))
            existing_ids: set[int] = {row[0] for row in existing_result}
            logger.info(f"CDB sync: {len(existing_ids)} cards already in DB")

            # Parse all CDB files in a thread, merging by ID
            cards_to_insert, stats = await asyncio.to_thread(
                self._parse_all_cdbs,
                [p for p, _ in paths],
                existing_ids,
            )

            logger.info(
                f"CDB total across files: {stats['total_in_cdbs']}, "
                f"new to insert: {len(cards_to_insert)} "
                f"(prerelease: {stats['prerelease_count']})"
            )

            # Insert new cards — ON CONFLICT DO NOTHING (never overwrite YGOProDeck data)
            inserted = 0
            for i in range(0, len(cards_to_insert), BATCH_SIZE):
                batch = cards_to_insert[i : i + BATCH_SIZE]
                stmt = pg_insert(_CARD_TABLE).values(batch).on_conflict_do_nothing(
                    index_elements=["external_card_id"]
                )
                await db.execute(stmt)
                await db.commit()
                inserted += len(batch)
                logger.info(f"CDB sync progress: {inserted}/{len(cards_to_insert)}")

            sync_run.status = SyncStatus.completed
            sync_run.finished_at = datetime.utcnow()
            sync_run.summary_json = {
                "sources": [str(p) for p, _ in paths],
                **stats,
                "new_inserted": inserted,
            }
            await db.commit()
            logger.info(f"CDB sync complete: {inserted} new cards inserted")

        finally:
            for p, is_temp in paths:
                if is_temp and p.exists():
                    p.unlink(missing_ok=True)

    async def _download(self, url: str) -> Path:
        tmp = Path(tempfile.mktemp(suffix=".cdb"))
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as f:
                    async for chunk in resp.aiter_bytes(65536):
                        f.write(chunk)
        logger.info(f"Downloaded {tmp.name} ({tmp.stat().st_size / 1024:.0f} KB)")
        return tmp

    def _parse_all_cdbs(
        self, paths: list[Path], existing_ids: set[int]
    ) -> tuple[list[dict], dict]:
        """
        Merge cards from all CDB files. Later files override earlier ones on ID conflict.
        Returns (cards_to_insert, stats_dict).
        """
        merged: dict[int, dict] = {}   # ext_id → card_dict
        total_raw = 0
        prerelease_count = 0

        for path in paths:
            if not path.exists():
                logger.warning(f"CDB file not found, skipping: {path}")
                continue
            file_cards, file_total = self._parse_single_cdb(path)
            total_raw += file_total
            for card in file_cards:
                merged[card["external_card_id"]] = card
                if card.get("_is_prerelease"):
                    prerelease_count += 1

        # Only keep cards not already in DB
        cards_to_insert = [
            {k: v for k, v in c.items() if not k.startswith("_")}
            for c in merged.values()
            if c["external_card_id"] not in existing_ids
        ]

        return cards_to_insert, {
            "total_in_cdbs": len(merged),
            "total_raw_rows": total_raw,
            "prerelease_count": prerelease_count,
            "already_in_db": len(existing_ids),
        }

    def _parse_single_cdb(self, cdb_path: Path) -> tuple[list[dict], int]:
        """Parse one CDB file and return (card_list, raw_row_count)."""
        con = sqlite3.connect(str(cdb_path))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                """
                SELECT d.id, d.ot, d.type, d.atk, d.def, d.level,
                       d.race, d.attribute, d.alias,
                       t.name, t.desc
                FROM datas d
                JOIN texts t ON t.id = d.id
                """
            ).fetchall()
        finally:
            con.close()

        cards: list[dict] = []
        for row in rows:
            ot: int = row["ot"]
            if not _is_valid_ot(ot):
                continue
            if row["alias"] != 0:
                continue  # skip alt-art duplicates

            ext_id: int = row["id"]
            name: str = (row["name"] or "").strip()
            if not name:
                continue

            cdb_type: int = row["type"]
            cdb_race: int = row["race"]
            cdb_level: int = row["level"]
            cdb_attr: int = row["attribute"]
            raw_atk: int = row["atk"]
            raw_def: int = row["def"]

            level_val, scale_l, scale_r = decode_level(cdb_level)
            is_link = bool(cdb_type & 0x400000)
            is_prerelease = bool(ot & 0x100)

            cards.append({
                "external_card_id": ext_id,
                "name": name,
                "slug": f"{slugify(name)}-{ext_id}",
                "type": decode_type_string(cdb_type, cdb_race),
                "frame_type": decode_frame_type(cdb_type),
                "race": decode_race(cdb_type, cdb_race),
                "attribute": decode_attribute(cdb_attr),
                "archetype": None,
                "level_rank_link": level_val if level_val else None,
                "atk": raw_atk if raw_atk != _UNKNOWN_ATK_DEF else None,
                "def": raw_def if raw_def not in (_UNKNOWN_ATK_DEF, -1) else None,
                "scale": scale_l,
                "linkval": level_val if is_link else None,
                "description": (row["desc"] or "").strip() or None,
                "pend_description": None,
                "monster_description": None,
                "tcg_date": None,
                "ocg_date": None,
                # internal flag stripped before DB insert
                "_is_prerelease": is_prerelease,
            })

        return cards, len(rows)


card_cdb_service = CardCdbService()
