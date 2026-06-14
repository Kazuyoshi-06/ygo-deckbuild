from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class MatchResultIn(BaseModel):
    opponent_arch: str
    result: Literal["W", "L", "D"]
    event_date: date | None = None
    notes: str | None = None

    @field_validator("opponent_arch")
    @classmethod
    def clean_arch(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("opponent_arch must not be empty")
        return v[:255]


class MatchResultRow(BaseModel):
    id: int
    opponent_arch: str
    result: str
    event_date: date | None
    notes: str | None
    created_at: datetime


class MatchupSummary(BaseModel):
    opponent_arch: str
    wins: int
    losses: int
    draws: int
    total: int
    win_rate: float          # (W + 0.5×D) / total


class DeckMatchupOut(BaseModel):
    deck_id: int
    deck_title: str
    archetype_label: str | None
    total_matches: int
    overall_wins: int
    overall_losses: int
    overall_draws: int
    overall_win_rate: float
    matchup_stats: list[MatchupSummary]
    recent_results: list[MatchResultRow]


class MatrixCell(BaseModel):
    wins: int
    losses: int
    draws: int
    total: int
    win_rate: float | None   # None when no data


class ArchetypeMatrixRow(BaseModel):
    archetype: str
    total_matches: int
    avg_win_rate: float | None
    vs: dict[str, MatrixCell]  # opponent_arch → cell


class MatchupMatrixOut(BaseModel):
    archetypes: list[str]        # all archetypes present (sorted by total matches desc)
    rows: list[ArchetypeMatrixRow]
    total_matches: int
    has_data: bool
