from collections import defaultdict
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Input schemas ────────────────────────────────────────────────────────────

class DeckCardIn(BaseModel):
    card_id: int
    section: Literal['main', 'extra', 'side']
    quantity: int = Field(ge=1, le=3)


class DeckCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    archetype_label: str | None = None
    notes: str | None = None
    cards: list[DeckCardIn] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_deck_structure(self) -> 'DeckCreateIn':
        copies: defaultdict[int, int] = defaultdict(int)
        totals: dict[str, int] = {'main': 0, 'extra': 0, 'side': 0}

        for c in self.cards:
            copies[c.card_id] += c.quantity
            totals[c.section] += c.quantity

        over = [cid for cid, n in copies.items() if n > 3]
        if over:
            raise ValueError(f'Card IDs {over} exceed the 3-copy limit')
        if totals['main'] > 60:
            raise ValueError(f'Main deck has {totals["main"]} cards — maximum is 60')
        if totals['extra'] > 15:
            raise ValueError(f'Extra deck has {totals["extra"]} cards — maximum is 15')
        if totals['side'] > 15:
            raise ValueError(f'Side deck has {totals["side"]} cards — maximum is 15')

        return self


class DeckUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    archetype_label: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class UrlImportIn(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(default=None, max_length=255)


class TextImportIn(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    title: str | None = Field(default=None, max_length=255)


class TextImportOut(BaseModel):
    deck_id: int
    submission_id: int
    title: str
    main_count: int
    extra_count: int
    side_count: int
    unknown_names: list[str]


class BulkImportItemOut(BaseModel):
    filename: str
    deck_id: int | None = None
    submission_id: int | None = None
    title: str
    main_count: int = 0
    extra_count: int = 0
    side_count: int = 0
    unknown_ids: list[int] = Field(default_factory=list)
    error: str | None = None


class BulkImportOut(BaseModel):
    imported: int
    failed: int
    items: list[BulkImportItemOut]


# ── Output schemas ───────────────────────────────────────────────────────────

class DeckImportOut(BaseModel):
    deck_id: int
    submission_id: int
    title: str
    main_count: int
    extra_count: int
    side_count: int
    unknown_ids: list[int]


class DeckCardOut(BaseModel):
    card_id: int
    external_card_id: int
    name: str
    section: str
    quantity: int
    image_url: str
    tcg_date: datetime | None = None
    ocg_date: datetime | None = None
    cardmarket_price: float | None = None
    tcgplayer_price: float | None = None


class DeckDetailOut(BaseModel):
    id: int
    title: str
    archetype_label: str | None = None
    source_type: str
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    main: list[DeckCardOut]
    extra: list[DeckCardOut]
    side: list[DeckCardOut]
    main_count: int
    extra_count: int
    side_count: int
    budget_cardmarket: float | None = None
    budget_tcgplayer: float | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: list | None) -> list:
        return v or []


class DeckSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    archetype_label: str | None = None
    source_type: str
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: list | None) -> list:
        return v or []


class DeckListOut(BaseModel):
    items: list[DeckSummaryOut]
    total: int
    page: int
    limit: int
