from datetime import date

from pydantic import BaseModel, Field


class SubmitResultIn(BaseModel):
    deck_id: int
    # Tournament
    tournament_name: str = Field(min_length=1, max_length=255)
    tournament_date: date
    tournament_format: str = Field(default="TCG", max_length=50)
    tournament_location: str | None = Field(default=None, max_length=255)
    tournament_participants: int | None = Field(default=None, ge=2)
    # Player
    player_name: str = Field(min_length=1, max_length=255)
    player_country: str | None = Field(default=None, max_length=100)
    # Result
    placement: int = Field(ge=1)
    wins: int | None = Field(default=None, ge=0)
    losses: int | None = Field(default=None, ge=0)
    draws: int | None = Field(default=None, ge=0)


class TournamentOut(BaseModel):
    id: int
    name: str
    event_date: date | None
    format: str | None
    location: str | None
    participants_count: int | None


class PlayerOut(BaseModel):
    id: int
    display_name: str
    country: str | None


class SubmitResultOut(BaseModel):
    tournament: TournamentOut
    player: PlayerOut
    deck_id: int
    submission_id: int
    placement: int


class TournamentEntryOut(BaseModel):
    submission_id: int
    deck_id: int
    deck_title: str
    archetype_label: str | None
    player_name: str | None
    player_country: str | None
    placement: int | None
    wins: int | None
    losses: int | None
    draws: int | None


class TournamentSummaryOut(BaseModel):
    id: int
    name: str
    event_date: date | None
    format: str | None
    location: str | None
    participants_count: int | None
    entry_count: int


class TournamentDetailOut(BaseModel):
    id: int
    name: str
    organizer: str | None
    event_date: date | None
    format: str | None
    location: str | None
    participants_count: int | None
    notes: str | None
    entries: list[TournamentEntryOut]
