from datetime import date

from pydantic import BaseModel


class BanlistSummaryOut(BaseModel):
    id: int
    format: str
    effective_date: date
    version_label: str | None = None
    forbidden_count: int
    limited_count: int
    semi_limited_count: int


class BanlistEntryOut(BaseModel):
    card_id: int
    external_card_id: int
    name: str
    image_url: str
    status: str
    limit_value: int


class BanlistDetailOut(BaseModel):
    id: int
    format: str
    effective_date: date
    version_label: str | None = None
    forbidden: list[BanlistEntryOut]
    limited: list[BanlistEntryOut]
    semi_limited: list[BanlistEntryOut]


class LatestBanlistsOut(BaseModel):
    tcg: BanlistSummaryOut | None = None
    ocg: BanlistSummaryOut | None = None


class LegalityViolation(BaseModel):
    card_id: int
    name: str
    status: str
    limit_value: int
    actual_quantity: int


class RestrictedCard(BaseModel):
    card_id: int
    name: str
    status: str
    limit_value: int


class DeckLegalityOut(BaseModel):
    deck_id: int
    banlist_id: int | None = None
    format: str
    is_legal: bool
    violations: list[LegalityViolation]
    restricted: list[RestrictedCard] = []
