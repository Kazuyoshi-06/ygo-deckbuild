"""
RQ job functions — must be synchronous.

Each function wraps an async service method via asyncio.run(),
creating a fresh event loop for the worker process.
"""

import asyncio

from app.services.banlist_sync_service import banlist_sync_service
from app.services.card_cdb_service import card_cdb_service
from app.services.card_sync import card_sync_service


def run_card_sync(sync_run_id: int) -> None:
    asyncio.run(card_sync_service.execute(sync_run_id))


def run_banlist_sync(sync_run_id: int) -> None:
    asyncio.run(banlist_sync_service.execute(sync_run_id))


def run_cdb_sync(sync_run_id: int, sources: list[str]) -> None:
    asyncio.run(card_cdb_service.execute(sync_run_id, sources))
