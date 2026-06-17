import logging
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection, DeckSourceType
from app.schemas.deck import DeckCreateIn, DeckImportOut, TextImportOut
from app.services import cache_service
from app.services.text_import_service import EXTRA_FRAME_TYPES, ParsedTextDeck
from app.services.ydk_parser import ParsedYdk

logger = logging.getLogger(__name__)

_SECTION_ENUM = {
    "main": CardSection.main,
    "extra": CardSection.extra,
    "side": CardSection.side,
}


async def _insert_deck(
    db: AsyncSession,
    title: str,
    source_type: DeckSourceType,
    archetype_label: str | None = None,
    notes: str | None = None,
) -> tuple[Deck, DeckSubmission]:
    deck = Deck(
        title=title,
        archetype_label=archetype_label,
        notes=notes,
        source_type=source_type,
    )
    db.add(deck)
    await db.flush()

    submission = DeckSubmission(deck_id=deck.id)
    db.add(submission)
    await db.flush()
    return deck, submission


class DeckImportService:
    async def import_ydk(
        self,
        db: AsyncSession,
        parsed: ParsedYdk,
        title: str,
        source_type: DeckSourceType = DeckSourceType.ydk_import,
    ) -> DeckImportOut:
        all_ids = set(parsed.main + parsed.extra + parsed.side)
        rows = await db.execute(
            select(Card).where(Card.external_card_id.in_(all_ids))
        )
        card_map: dict[int, Card] = {c.external_card_id: c for c in rows.scalars()}
        unknown_ids = sorted(all_ids - set(card_map))

        deck, submission = await _insert_deck(db, title, source_type)

        deck_cards: list[DeckCard] = []
        counts: dict[str, int] = {}

        for section_name, raw_ids in [
            ("main", parsed.main),
            ("extra", parsed.extra),
            ("side", parsed.side),
        ]:
            aggregated = Counter(raw_ids)
            known_total = 0
            for ext_id, qty in aggregated.items():
                card = card_map.get(ext_id)
                if card:
                    deck_cards.append(
                        DeckCard(
                            deck_submission_id=submission.id,
                            card_id=card.id,
                            section=_SECTION_ENUM[section_name],
                            quantity=qty,
                        )
                    )
                    known_total += qty
            counts[section_name] = known_total

        db.add_all(deck_cards)
        await db.commit()
        await cache_service.invalidate_all()

        logger.info(
            "YDK imported: deck_id=%s title=%r main=%s extra=%s side=%s unknown=%s",
            deck.id, title, counts["main"], counts["extra"], counts["side"], len(unknown_ids),
        )

        return DeckImportOut(
            deck_id=deck.id,
            submission_id=submission.id,
            title=title,
            main_count=counts["main"],
            extra_count=counts["extra"],
            side_count=counts["side"],
            unknown_ids=unknown_ids,
        )

    async def create_manual(
        self,
        db: AsyncSession,
        data: DeckCreateIn,
    ) -> DeckImportOut:
        deck, submission = await _insert_deck(
            db, data.title, DeckSourceType.manual,
            archetype_label=data.archetype_label,
            notes=data.notes,
        )

        counts: dict[str, int] = {"main": 0, "extra": 0, "side": 0}
        deck_cards: list[DeckCard] = []

        for card_in in data.cards:
            section_enum = _SECTION_ENUM.get(card_in.section)
            if not section_enum:
                continue
            deck_cards.append(
                DeckCard(
                    deck_submission_id=submission.id,
                    card_id=card_in.card_id,
                    section=section_enum,
                    quantity=card_in.quantity,
                )
            )
            counts[card_in.section] += card_in.quantity

        db.add_all(deck_cards)
        await db.commit()
        await cache_service.invalidate_all()

        logger.info(
            "Manual deck created: deck_id=%s title=%r main=%s extra=%s side=%s",
            deck.id, data.title, counts["main"], counts["extra"], counts["side"],
        )

        return DeckImportOut(
            deck_id=deck.id,
            submission_id=submission.id,
            title=data.title,
            main_count=counts["main"],
            extra_count=counts["extra"],
            side_count=counts["side"],
            unknown_ids=[],
        )


    async def import_text(
        self,
        db: AsyncSession,
        parsed: ParsedTextDeck,
        title: str,
    ) -> TextImportOut:
        """Import a deck from a parsed text deck list (name-based lookup)."""
        all_entries = parsed.all_entries()
        unique_names_lower = list({name.lower() for name, _, _ in all_entries})

        # Batch-fetch cards by name (case-insensitive)
        rows = await db.execute(
            select(Card).where(func.lower(Card.name).in_(unique_names_lower))
        )
        card_map: dict[str, Card] = {c.name.lower(): c for c in rows.scalars()}

        deck, submission = await _insert_deck(db, title, DeckSourceType.manual)

        deck_cards: list[DeckCard] = []
        counts: dict[str, int] = {'main': 0, 'extra': 0, 'side': 0}
        seen_unknown: set[str] = set()
        unknown_names: list[str] = []

        # Aggregate quantity per (name_lower, section)
        agg: dict[tuple[str, str], int] = {}
        for name, qty, section in all_entries:
            key = (name.lower(), section)
            agg[key] = agg.get(key, 0) + qty

        for (name_lower, section), qty in agg.items():
            card = card_map.get(name_lower)
            if not card:
                orig = next(
                    (n for n, _, s in all_entries if n.lower() == name_lower and s == section),
                    name_lower,
                )
                if orig not in seen_unknown:
                    seen_unknown.add(orig)
                    unknown_names.append(orig)
                continue

            # Auto-promote extra-deck monsters from main to extra
            effective_section = section
            if section == 'main' and card.frame_type in EXTRA_FRAME_TYPES:
                effective_section = 'extra'

            effective_qty = min(qty, 3)
            deck_cards.append(
                DeckCard(
                    deck_submission_id=submission.id,
                    card_id=card.id,
                    section=_SECTION_ENUM[effective_section],
                    quantity=effective_qty,
                )
            )
            counts[effective_section] += effective_qty

        db.add_all(deck_cards)
        await db.commit()
        await cache_service.invalidate_all()

        logger.info(
            "Text import: deck_id=%s title=%r main=%s extra=%s side=%s unknown=%s",
            deck.id, title, counts['main'], counts['extra'], counts['side'], len(unknown_names),
        )

        return TextImportOut(
            deck_id=deck.id,
            submission_id=submission.id,
            title=title,
            main_count=counts['main'],
            extra_count=counts['extra'],
            side_count=counts['side'],
            unknown_names=unknown_names,
        )


deck_import_service = DeckImportService()
