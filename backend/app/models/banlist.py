from datetime import date, datetime

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.enums import BanlistStatus


class Banlist(Base):
    __tablename__ = "banlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    format: Mapped[str] = mapped_column(String(50))
    source_name: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(512))
    effective_date: Mapped[date] = mapped_column(Date)
    version_label: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    entries: Mapped[list["BanlistEntry"]] = relationship(back_populates="banlist", cascade="all, delete-orphan")
    deck_submissions: Mapped[list["DeckSubmission"]] = relationship(back_populates="banlist")

    __table_args__ = (
        Index("ix_banlists_format_effective_date", "format", "effective_date"),
    )


class BanlistEntry(Base):
    __tablename__ = "banlist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    banlist_id: Mapped[int] = mapped_column(ForeignKey("banlists.id", ondelete="CASCADE"))
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    status: Mapped[BanlistStatus] = mapped_column(SAEnum(BanlistStatus, name="banliststatus"))
    limit_value: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    banlist: Mapped["Banlist"] = relationship(back_populates="entries")
    card: Mapped["Card"] = relationship(back_populates="banlist_entries")

    __table_args__ = (
        Index("ix_banlist_entries_banlist_id_card_id", "banlist_id", "card_id"),
    )
