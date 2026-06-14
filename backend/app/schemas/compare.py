from datetime import datetime

from pydantic import BaseModel


class DeckMeta(BaseModel):
    id: int
    title: str
    archetype_label: str | None
    tags: list[str]
    created_at: datetime


class ComparedCard(BaseModel):
    card_id: int
    external_card_id: int
    name: str
    type: str
    frame_type: str
    image_url: str
    presence_pct: float
    quantities: list[int]   # one per deck, in same order as CompareOut.deck_ids


class DeckRatios(BaseModel):
    main_count: int = 0
    monster_count: int = 0
    spell_count: int = 0
    trap_count: int = 0
    extra_count: int = 0
    side_count: int = 0


class CompareOut(BaseModel):
    deck_ids: list[int]
    decks: list[DeckMeta]
    core: list[ComparedCard]    # present in 100% of decks
    flex: list[ComparedCard]    # present in 50–99% of decks
    unique: list[ComparedCard]  # present in <50% of decks
    ratios: list[DeckRatios]    # one per deck, same order as deck_ids
    divergence_score: float     # 0 = identical, 1 = completely different
