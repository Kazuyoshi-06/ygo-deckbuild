from pydantic import BaseModel


class StarterDistEntry(BaseModel):
    count: int        # 0, 1, 2, 3+ starters in hand
    simulations: int
    pct: float


class CardBrickRate(BaseModel):
    card_id: int
    name: str
    role: str | None
    total_appearances: int       # across all simulations
    dead_appearances: int        # appearances in dead hands (0 starter, 0 handtrap)
    dead_pct: float              # dead_appearances / total_appearances


class SimulationOut(BaseModel):
    deck_id: int
    deck_title: str
    main_count: int
    n_simulations: int
    hand_size: int
    has_roles: bool
    win_rate: float              # P(≥1 starter in hand)
    medium_rate: float           # P(0 starter, ≥1 handtrap)
    dead_rate: float             # P(0 starter, 0 handtrap)
    avg_starters: float
    avg_handtraps: float
    avg_garnets: float
    starter_dist: list[StarterDistEntry]
    brick_cards: list[CardBrickRate]   # sorted by dead_pct desc
