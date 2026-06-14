from pydantic import BaseModel


class SideCardInfo(BaseModel):
    card_id: int
    name: str
    frame_type: str
    image_url: str
    quantity: int          # copies in current side (0 for suggestions)
    role: str | None
    global_side_pct: float  # fraction of other DB decks that include this card in side


class ArchetypeSideCard(BaseModel):
    card_id: int
    name: str
    frame_type: str
    image_url: str
    side_pct: float        # fraction of decks of this archetype that side this card


class ArchetypeSideData(BaseModel):
    archetype_label: str
    deck_count: int
    top_side_cards: list[ArchetypeSideCard]  # top 15


class SideOptimizerOut(BaseModel):
    deck_id: int
    deck_title: str
    side_count: int
    current_side: list[SideCardInfo]
    suggestions: list[SideCardInfo]          # ranked by global popularity
    total_other_decks: int
    has_side_data: bool
    archetypes: list[ArchetypeSideData]       # archetype × top-15 side cards matrix
