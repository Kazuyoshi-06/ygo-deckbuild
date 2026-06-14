from pydantic import BaseModel


class CardTrend(BaseModel):
    card_id: int
    name: str
    frame_type: str
    monthly_presence: list[float]   # parallel to EvolutionOut.months
    trend: str                       # "rising_strong"|"rising"|"stable"|"falling"|"falling_strong"
    slope: float                     # pct-points per month (last 3 data points)
    avg_presence: float
    peak_presence: float


class EvolutionOut(BaseModel):
    archetype_label: str
    months: list[str]        # "YYYY-MM" strings, chronological
    deck_counts: list[int]   # parallel to months
    total_decks: int
    cards: list[CardTrend]   # sorted: rising_strong → rising → stable → falling → falling_strong
    has_data: bool
