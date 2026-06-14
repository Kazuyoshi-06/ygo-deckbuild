from datetime import date, datetime

from sqlalchemy import JSON, Date, Enum as SAEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.enums import CardSection, DeckSourceType


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    archetype_label: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[DeckSourceType] = mapped_column(
        SAEnum(DeckSourceType, name="decksourcetype"), default=DeckSourceType.manual
    )
    source_url: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    submissions: Mapped[list["DeckSubmission"]] = relationship(back_populates="deck", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_decks_archetype_label", "archetype_label"),
    )


class DeckSubmission(Base):
    __tablename__ = "deck_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"))
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id", ondelete="SET NULL"))
    tournament_id: Mapped[int | None] = mapped_column(ForeignKey("tournaments.id", ondelete="SET NULL"))
    format: Mapped[str | None] = mapped_column(String(50))
    placement: Mapped[int | None] = mapped_column(Integer)
    wins: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    draws: Mapped[int | None] = mapped_column(Integer)
    event_date: Mapped[date | None] = mapped_column(Date)
    banlist_id: Mapped[int | None] = mapped_column(ForeignKey("banlists.id", ondelete="SET NULL"))
    participants_count: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    deck: Mapped["Deck"] = relationship(back_populates="submissions")
    player: Mapped["Player | None"] = relationship(back_populates="deck_submissions")
    tournament: Mapped["Tournament | None"] = relationship(back_populates="deck_submissions")
    banlist: Mapped["Banlist | None"] = relationship(back_populates="deck_submissions")
    cards: Mapped[list["DeckCard"]] = relationship(back_populates="submission", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_deck_submissions_format_event_date", "format", "event_date"),
        Index("ix_deck_submissions_deck_id", "deck_id"),
    )


class DeckCard(Base):
    __tablename__ = "deck_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_submission_id: Mapped[int] = mapped_column(ForeignKey("deck_submissions.id", ondelete="CASCADE"))
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="RESTRICT"))
    section: Mapped[CardSection] = mapped_column(SAEnum(CardSection, name="cardsection"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    submission: Mapped["DeckSubmission"] = relationship(back_populates="cards")
    card: Mapped["Card"] = relationship(back_populates="deck_cards")

    __table_args__ = (
        Index("ix_deck_cards_deck_submission_id", "deck_submission_id"),
    )
