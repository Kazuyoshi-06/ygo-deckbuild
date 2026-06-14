"""
Seed de données minimales pour les tests locaux.
Usage : python -m app.seeds
"""

import asyncio

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.models import Card, SyncRun
from app.models.enums import SyncStatus, SyncType


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM cards"))
        count = result.scalar()
        if count and count > 0:
            print(f"Base déjà peuplée ({count} cartes). Seed ignoré.")
            return

        sample_card = Card(
            external_card_id=89631139,
            name="Blue-Eyes White Dragon",
            slug="blue-eyes-white-dragon",
            type="Normal Monster",
            frame_type="normal",
            race="Dragon",
            attribute="LIGHT",
            archetype="Blue-Eyes",
            level_rank_link=8,
            atk=3000,
            def_=2500,
            description=(
                "This legendary dragon is a powerful engine of destruction. "
                "Virtually invincible, very few have faced this awesome creature and lived to tell the tale."
            ),
        )

        sync_run = SyncRun(
            sync_type=SyncType.cards,
            status=SyncStatus.completed,
            summary_json={"seeded": 1, "note": "dev seed"},
        )

        session.add(sample_card)
        session.add(sync_run)
        await session.commit()
        print("Seed OK — 1 carte insérée (Blue-Eyes White Dragon), 1 sync_run créé.")


if __name__ == "__main__":
    asyncio.run(seed())
