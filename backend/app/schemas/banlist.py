from datetime import date

from pydantic import BaseModel


class BanlistSummaryOut(BaseModel):
    id: int
    format: str
    effective_date: date
    version_label: str | None = None
    forbidden_count: int
    limited_count: int
    semi_limited_count: int


class BanlistEntryOut(BaseModel):
    card_id: int
    external_card_id: int
    name: str
    image_url: str
    status: str
    limit_value: int


class BanlistDetailOut(BaseModel):
    id: int
    format: str
    effective_date: date
    version_label: str | None = None
    forbidden: list[BanlistEntryOut]
    limited: list[BanlistEntryOut]
    semi_limited: list[BanlistEntryOut]


class LatestBanlistsOut(BaseModel):
    tcg: BanlistSummaryOut | None = None
    ocg: BanlistSummaryOut | None = None


class LegalityViolation(BaseModel):
    card_id: int
    name: str
    status: str
    limit_value: int
    actual_quantity: int


class RestrictedCard(BaseModel):
    card_id: int
    name: str
    status: str
    limit_value: int


class BanlistCardHistoryEntry(BaseModel):
    banlist_id: int
    format: str
    effective_date: date
    version_label: str | None
    status: str


class BanlistDiffEntry(BaseModel):
    card_id: int
    external_card_id: int
    name: str
    image_url: str
    from_status: str | None
    to_status: str | None


class BanlistDiffOut(BaseModel):
    from_banlist: BanlistSummaryOut
    to_banlist: BanlistSummaryOut
    hits: list[BanlistDiffEntry]    # more restricted in 'to'
    shifts: list[BanlistDiffEntry]  # still restricted but eased
    frees: list[BanlistDiffEntry]   # fully removed in 'to'


class ReplacementCandidate(BaseModel):
    card_id: int
    name: str
    image_url: str
    frame_type: str
    before_pct: float    # frequency among affected decks before the ban (0–1)
    after_pct: float     # frequency among affected decks after the ban (0–1)
    delta: float          # after_pct - before_pct


class CardReplacementsOut(BaseModel):
    card_id: int
    card_name: str
    format: str
    is_banned: bool
    ban_date: date | None = None
    affected_archetypes: list[str]
    before_deck_count: int
    after_deck_count: int
    replacements: list[ReplacementCandidate]
    has_data: bool


class BanlistRiskEntry(BaseModel):
    card_id: int
    name: str
    image_url: str
    archetype: str | None
    frame_type: str
    play_rate: float       # 0–1, share of decks in the database playing this card
    deck_count: int
    is_recent: bool         # released within ~12 months in the requested format
    prior_hits: int         # number of past banlist periods this card was restricted in `format`
    risk_score: float       # 0–1 composite heuristic
    risk_label: str          # "Low" | "Moderate" | "High" | "Very High"


class BanlistPredictionOut(BaseModel):
    format: str
    total_decks_analyzed: int
    candidates: list[BanlistRiskEntry]    # currently-unrestricted cards, sorted by risk_score desc
    has_data: bool
    disclaimer: str


class DeckLegalityOut(BaseModel):
    deck_id: int
    banlist_id: int | None = None
    format: str
    is_legal: bool
    violations: list[LegalityViolation]
    restricted: list[RestrictedCard] = []
