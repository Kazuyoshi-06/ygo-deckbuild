from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class DeckUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    archetype_label: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


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
