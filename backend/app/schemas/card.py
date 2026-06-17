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
    cardmarket_price: float | None = None
    tcgplayer_price: float | None = None
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


class CurrentBanlistStatus(BaseModel):
    tcg: str | None = None
    ocg: str | None = None


class DeckUsingCardOut(BaseModel):
    deck_id: int
    title: str
    archetype_label: str | None = None


class CardDetailOut(CardOut):
    pend_description: str | None = None
    monster_description: str | None = None
    current_banlist_status: CurrentBanlistStatus
    decks_using: list[DeckUsingCardOut]
    decks_using_total: int
