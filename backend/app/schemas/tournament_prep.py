from pydantic import BaseModel

from app.schemas.banlist import DeckLegalityOut


class ExpectedMetaEntry(BaseModel):
    label: str
    meta_share: float    # 0–1
    deck_count: int


class WeightedSideCard(BaseModel):
    card_id: int
    name: str
    frame_type: str
    image_url: str
    weighted_score: float                    # sum of meta_share * side_pct across expected archetypes
    archetype_coverage: dict[str, float]      # archetype_label -> side_pct in that archetype's matrix


class TournamentPrepOut(BaseModel):
    deck_id: int
    deck_title: str
    expected_meta: list[ExpectedMetaEntry]          # top archetypes, highest meta_share first
    meta_source: str                                 # "tournament" | "deck_database"
    side_recommendations: list[WeightedSideCard]     # top 15 by weighted_score
    has_side_data: bool
    legality_tcg: DeckLegalityOut
    legality_ocg: DeckLegalityOut
