from pydantic import BaseModel, field_validator

VALID_ROLES = frozenset({
    "starter", "extender", "handtrap", "garnet", "tech", "boss", "other"
})


class DeckCardRoleIn(BaseModel):
    role: str | None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)} or null")
        return v


class CardProbRow(BaseModel):
    card_id: int
    external_card_id: int
    name: str
    frame_type: str
    image_url: str
    total_in_main: int      # total copies in main deck
    role: str | None
    p_at_least_one_5: float  # P(≥1 in 5-card hand)
    p_at_least_one_6: float  # P(≥1 in 6-card hand, going second)
    p_zero_5: float          # P(0 in 5-card hand) — useful for garnets


class GroupStats(BaseModel):
    role: str
    total_copies: int
    p_at_least_one_5: float
    p_at_least_one_6: float


class Recommendation(BaseModel):
    level: str   # 'info' | 'warning' | 'critical'
    text: str


class ProbabilityOut(BaseModel):
    deck_id: int
    deck_title: str
    main_count: int
    cards: list[CardProbRow]       # main deck cards, deduplicated by card_id
    groups: list[GroupStats]       # one per role that has cards
    dead_hand_p5: float            # P(0 starters AND 0 handtraps in 5)
    dead_hand_p6: float            # P(0 starters AND 0 handtraps in 6)
    has_roles: bool                # whether any roles are assigned
    recommendations: list[Recommendation]
