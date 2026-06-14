import hashlib
import logging
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Card, CardImage
from app.models.enums import ImageStatus

logger = logging.getLogger(__name__)

# Resolved once at startup so background tasks use the same absolute path.
_MEDIA_ROOT: Path = (
    Path(settings.storage_local_path)
    if Path(settings.storage_local_path).is_absolute()
    else Path.cwd() / settings.storage_local_path
)
_CARDS_DIR = _MEDIA_ROOT / "cards"


def _source_url(external_card_id: int) -> str:
    return f"https://images.ygoprodeck.com/images/cards/{external_card_id}.jpg"


class ImageService:
    async def get_image_url(
        self,
        card: Card,
        db: AsyncSession,
        background_tasks,
    ) -> str:
        """Return the URL for a card image.

        Checks local cache first. If not ready, queues a background download
        and returns the placeholder URL.
        """
        image = await db.scalar(
            select(CardImage).where(
                CardImage.card_id == card.id,
                CardImage.image_kind == "normal",
            )
        )

        if image is not None and image.status == ImageStatus.ready and image.local_path:
            image.last_accessed_at = datetime.utcnow()
            await db.commit()
            return f"/media/{image.local_path}"

        if image is None:
            image = CardImage(
                card_id=card.id,
                source_url=_source_url(card.external_card_id),
                image_kind="normal",
                status=ImageStatus.queued,
            )
            db.add(image)
            await db.commit()
            await db.refresh(image)
            background_tasks.add_task(self._download, image.id)
        elif image.status == ImageStatus.missing:
            # Permanent 404 from YGOProDeck (pre-release card) — serve card back, no retry
            return "/media/card-back.svg"
        elif image.status == ImageStatus.failed:
            # Transient error — re-queue for retry
            image.status = ImageStatus.queued
            image.source_url = _source_url(card.external_card_id)
            await db.commit()
            background_tasks.add_task(self._download, image.id)
        # If already queued: nothing to do, background task is already running

        return "/media/placeholder-card.svg"

    async def _download(self, image_id: int) -> None:
        """Download a card image and store it locally. Opens its own DB session."""
        async with AsyncSessionLocal() as db:
            image = await db.get(CardImage, image_id)
            if not image or image.status == ImageStatus.ready:
                return

            card = await db.get(Card, image.card_id)
            if not card:
                return

            source_url = _source_url(card.external_card_id)
            filename = f"cards/{card.external_card_id}.jpg"
            dest_path = _MEDIA_ROOT / filename

            try:
                async with httpx.AsyncClient(
                    timeout=30.0, verify=settings.verify_ssl
                ) as client:
                    response = await client.get(source_url)
                    response.raise_for_status()
                    content = response.content

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(content)

                image.local_path = filename
                image.storage_key = filename
                image.status = ImageStatus.ready
                image.mime_type = "image/jpeg"
                image.downloaded_at = datetime.utcnow()
                image.checksum = hashlib.md5(content).hexdigest()
                await db.commit()

                logger.info(
                    "Image downloaded: card %s → %s", card.external_card_id, filename
                )

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    # No image on YGOProDeck — pre-release or unknown card. Mark permanently.
                    logger.info(
                        "No image on YGOProDeck for card %s (404) — marking missing",
                        card.external_card_id,
                    )
                    try:
                        image.status = ImageStatus.missing
                        await db.commit()
                    except Exception:
                        pass
                else:
                    logger.exception(
                        "HTTP error downloading image for card %s (image_id=%s): %s",
                        card.external_card_id,
                        image_id,
                        exc.response.status_code,
                    )
                    try:
                        image.status = ImageStatus.failed
                        await db.commit()
                    except Exception:
                        pass
            except Exception:
                logger.exception(
                    "Failed to download image for card %s (image_id=%s)",
                    card.external_card_id,
                    image_id,
                )
                try:
                    image.status = ImageStatus.failed
                    await db.commit()
                except Exception:
                    pass


image_service = ImageService()
