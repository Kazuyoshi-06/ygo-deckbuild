from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_card_id: int
    name: str
    slug: str
    type: str
    frame_type: str
    race: str | None = None
    attribute: str | None = None
    archetype: str | None = None
    level_rank_link: int | None = None
    atk: int | None = None
    def_: int | None = None
    scale: int | None = None
    linkval: int | None = None
    description: str | None = None
    tcg_date: datetime | None = None
    ocg_date: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def image_url(self) -> str:
        return f"/api/v1/cards/{self.id}/image"


class CardListOut(BaseModel):
    items: list[CardOut]
    total: int
    page: int
    limit: int
