from pydantic import BaseModel


class CardHit(BaseModel):
    id: int
    name: str
    type_label: str   # Monster | Spell | Trap | Other
    image_url: str


class DeckHit(BaseModel):
    id: int
    title: str
    archetype_label: str | None


class ArchetypeHit(BaseModel):
    label: str
    deck_count: int


class SearchOut(BaseModel):
    cards: list[CardHit]
    decks: list[DeckHit]
    archetypes: list[ArchetypeHit]
