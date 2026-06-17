"""One-off: run a full card sync synchronously (bypasses RQ) to backfill price columns.

Run with: cd backend && .venv\\Scripts\\python.exe -m scripts.run_price_sync
"""

import asyncio

from app.database import AsyncSessionLocal
from app.services.card_sync import card_sync_service


async def main() -> None:
    async with AsyncSessionLocal() as db:
        sync_run = await card_sync_service.trigger(db)
        run_id = sync_run.id
    await card_sync_service.execute(run_id)


if __name__ == "__main__":
    asyncio.run(main())
