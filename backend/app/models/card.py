from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.enums import ImageStatus


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_card_id: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    type: Mapped[str] = mapped_column(String(100))
    frame_type: Mapped[str] = mapped_column(String(50))
    race: Mapped[str | None] = mapped_column(String(100))
    attribute: Mapped[str | None] = mapped_column(String(50))
    archetype: Mapped[str | None] = mapped_column(String(255))
    level_rank_link: Mapped[int | None] = mapped_column()
    atk: Mapped[int | None] = mapped_column()
    def_: Mapped[int | None] = mapped_column("def")
    scale: Mapped[int | None] = mapped_column()
    linkval: Mapped[int | None] = mapped_column()
    description: Mapped[str | None] = mapped_column(Text)
    pend_description: Mapped[str | None] = mapped_column(Text)
    monster_description: Mapped[str | None] = mapped_column(Text)
    tcg_date: Mapped[datetime | None] = mapped_column()
    ocg_date: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    images: Mapped[list["CardImage"]] = relationship(back_populates="card", cascade="all, delete-orphan")
    banlist_entries: Mapped[list["BanlistEntry"]] = relationship(back_populates="card")
    deck_cards: Mapped[list["DeckCard"]] = relationship(back_populates="card")

    __table_args__ = (
        Index("ix_cards_name", "name"),
        Index("ix_cards_archetype", "archetype"),
        Index("ix_cards_external_card_id", "external_card_id"),
    )


class CardImage(Base):
    __tablename__ = "card_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    source_url: Mapped[str] = mapped_column(String(512))
    image_kind: Mapped[str] = mapped_column(String(50), default="normal")
    local_path: Mapped[str | None] = mapped_column(String(512))
    storage_key: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(50))
    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    status: Mapped[ImageStatus] = mapped_column(SAEnum(ImageStatus, name="imagestatus"), default=ImageStatus.missing)
    checksum: Mapped[str | None] = mapped_column(String(64))
    downloaded_at: Mapped[datetime | None] = mapped_column()
    last_accessed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    card: Mapped["Card"] = relationship(back_populates="images")

    __table_args__ = (
        Index("ix_card_images_card_id_status", "card_id", "status"),
        UniqueConstraint("card_id", "image_kind", name="uq_card_images_card_kind"),
    )
