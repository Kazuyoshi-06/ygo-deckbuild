from datetime import datetime

from pydantic import BaseModel

from app.schemas.evolution import EvolutionOut


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


class TechSuggestionsOut(BaseModel):
    archetype_label: str
    deck_count: int
    cards: list[CardFrequency]    # top tech cards (frequency < 0.25), sorted by deck_count desc


class ArchetypeCompareSummary(BaseModel):
    label: str
    deck_count: int
    meta_share: float    # deck_count / total decks in DB (0–1)
    avg_main_count: float
    avg_extra_count: float
    avg_side_count: float
    top_cards: list[CardFrequency]    # core + flex, sorted by frequency desc


class CommonCardEntry(BaseModel):
    card_id: int
    name: str
    image_url: str
    type_label: str
    frame_type: str
    frequencies: dict[str, float]    # archetype_label -> frequency (0–1)


class ArchetypeCompareOut(BaseModel):
    archetypes: list[ArchetypeCompareSummary]
    common_cards: list[CommonCardEntry]              # core/flex cards shared by every compared archetype
    exclusive_cards: dict[str, list[CardFrequency]]   # archetype_label -> core/flex cards unique to it
    evolution: dict[str, EvolutionOut]                # archetype_label -> monthly evolution series


class MetaWinShareEntry(BaseModel):
    label: str
    total_count: int     # submissions with placement data for this archetype
    top8_count: int      # of those, how many placed top 8
    meta_share: float    # total_count / all placed submissions (0–1)
    win_share: float     # top8_count / all top-8 placements (0–1)


class MetaWinShareOut(BaseModel):
    total_placed_submissions: int
    total_top8_submissions: int
    entries: list[MetaWinShareEntry]    # sorted by win_share desc
    has_data: bool                       # false if no tournament placement data exists yet


class TrendingArchetypeEntry(BaseModel):
    label: str
    trend: str             # "rising_strong"|"rising"|"falling"|"falling_strong" (never "stable" here)
    slope: float            # pct-points per week (last 3 weekly data points)
    current_share: float    # most recent week's meta share (0–1)
    deck_count: int         # submissions in the analyzed window


class TrendingArchetypesOut(BaseModel):
    weeks_analyzed: int
    rising: list[TrendingArchetypeEntry]     # sorted by slope desc
    falling: list[TrendingArchetypeEntry]    # sorted by slope asc (most negative first)
    has_data: bool


class OcgToTcgEntry(BaseModel):
    archetype: str
    ocg_release_date: datetime
    card_count: int
    predicted_tcg_date: datetime | None    # ocg_release_date + avg_gap_days, if a historical average is available


class OcgToTcgPipelineOut(BaseModel):
    avg_gap_days: float | None    # historical average OCG -> TCG release gap, across archetypes already in both
    sample_size: int               # number of crossed-over archetypes used to compute avg_gap_days
    pending: list[OcgToTcgEntry]   # OCG-exclusive archetypes, most recent OCG release first
    has_data: bool


class TopArchetype(BaseModel):
    label: str
    deck_count: int


class OverviewOut(BaseModel):
    total_decks: int
    total_cards_in_db: int
    total_archetypes: int
    top_archetypes: list[TopArchetype]
