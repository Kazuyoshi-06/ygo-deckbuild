from pydantic import BaseModel


class DistributionEntry(BaseModel):
    label: str
    count: int


class LevelEntry(BaseModel):
    level: int
    count: int


class DeckAnalyticsOut(BaseModel):
    deck_id: int
    title: str
    total_cards: int
    distinct_cards: int
    type_distribution: list[DistributionEntry]
    attribute_distribution: list[DistributionEntry]
    level_distribution: list[LevelEntry]
    frame_distribution: list[DistributionEntry]


class CardFrequency(BaseModel):
    card_id: int
    name: str
    image_url: str
    type_label: str       # Monster | Spell | Trap | Other
    frame_type: str       # effect | synchro | xyz | etc.
    deck_count: int
    frequency: float      # 0–1
    avg_quantity: float


class MonthlyEntry(BaseModel):
    month: str    # "YYYY-MM"
    count: int


class ArchetypeAnalyticsOut(BaseModel):
    archetype_label: str
    deck_count: int
    avg_main_count: float
    avg_extra_count: float
    avg_side_count: float
    core_cards: list[CardFrequency]    # frequency >= 0.75
    flex_cards: list[CardFrequency]    # 0.25 <= frequency < 0.75
    tech_cards: list[CardFrequency]    # frequency < 0.25
    monthly_submissions: list[MonthlyEntry]


class TopArchetype(BaseModel):
    label: str
    deck_count: int


class OverviewOut(BaseModel):
    total_decks: int
    total_cards_in_db: int
    total_archetypes: int
    top_archetypes: list[TopArchetype]
