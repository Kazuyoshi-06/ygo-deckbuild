import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CARD_INFO_PATH = "/cardinfo.php"
REQUEST_TIMEOUT = 120.0


class YGOProClient:
    def __init__(self) -> None:
        self._base_url = settings.ygopro_api_base

    async def _fetch(self, client: httpx.AsyncClient, params: dict) -> list[dict]:
        response = await client.get(f"{self._base_url}{CARD_INFO_PATH}", params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    async def fetch_all_cards(self) -> list[dict]:
        """Fetch the most complete card catalog: default pass + OCG-exclusive pass merged by ID."""
        logger.info("Fetching full card catalog from YGOPro API...")
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, verify=settings.verify_ssl) as client:
            default_cards = await self._fetch(client, {"misc": "yes"})
            ocg_cards = await self._fetch(client, {"misc": "yes", "format": "OCG"})

        seen_ids: set[int] = {c["id"] for c in default_cards}
        ocg_extras = [c for c in ocg_cards if c["id"] not in seen_ids]

        all_cards = default_cards + ocg_extras
        logger.info(
            f"Catalog: {len(default_cards)} default + {len(ocg_extras)} OCG-exclusive = {len(all_cards)} total"
        )
        return all_cards


ygopro_client = YGOProClient()
