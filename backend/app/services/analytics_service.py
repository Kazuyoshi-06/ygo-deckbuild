from collections import Counter, defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Card, Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection
from app.schemas.analytics import (
    ArchetypeAnalyticsOut,
    CardFrequency,
    DeckAnalyticsOut,
    DistributionEntry,
    LevelEntry,
    MonthlyEntry,
    OverviewOut,
    TopArchetype,
)

_FRAME_LABELS: dict[str, str] = {
    "normal": "Normal",
    "effect": "Effect",
    "ritual": "Ritual",
    "fusion": "Fusion",
    "synchro": "Synchro",
    "xyz": "XYZ",
    "link": "Link",
    "normal_pendulum": "Pendulum (Normal)",
    "effect_pendulum": "Pendulum (Effect)",
    "ritual_pendulum": "Pendulum (Ritual)",
    "fusion_pendulum": "Pendulum (Fusion)",
    "synchro_pendulum": "Pendulum (Synchro)",
    "xyz_pendulum": "Pendulum (XYZ)",
    "token": "Token",
    "skill": "Skill",
}


def _main_type(card_type: str) -> str:
    t = card_type.lower()
    if "monster" in t:
        return "Monster"
    if "spell" in t:
        return "Spell"
    if "trap" in t:
        return "Trap"
    return "Other"


async def _get_submission(deck_id: int, db: AsyncSession) -> DeckSubmission | None:
    row = await db.execute(
        select(DeckSubmission)
        .where(DeckSubmission.deck_id == deck_id)
        .options(selectinload(DeckSubmission.cards).selectinload(DeckCard.card))
        .order_by(DeckSubmission.created_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _get_submission_cards(deck_id: int, db: AsyncSession) -> list[DeckCard]:
    submission = await _get_submission(deck_id, db)
    return submission.cards if submission else []


async def get_deck_analytics(deck_id: int, db: AsyncSession) -> DeckAnalyticsOut | None:
    deck = await db.get(Deck, deck_id)
    if not deck:
        return None

    deck_cards = await _get_submission_cards(deck_id, db)

    type_counter: Counter[str] = Counter()
    attr_counter: Counter[str] = Counter()
    level_counter: Counter[int] = Counter()
    frame_counter: Counter[str] = Counter()
    total_cards = 0
    distinct_cards = 0

    for dc in deck_cards:
        card: Card = dc.card
        qty = dc.quantity
        total_cards += qty
        distinct_cards += 1

        main_type = _main_type(card.type)
        type_counter[main_type] += qty

        if card.attribute:
            attr_counter[card.attribute] += qty

        if card.level_rank_link is not None and main_type == "Monster":
            level_counter[card.level_rank_link] += qty

        frame_label = _FRAME_LABELS.get(card.frame_type, card.frame_type.replace("_", " ").title())
        frame_counter[frame_label] += qty

    return DeckAnalyticsOut(
        deck_id=deck_id,
        title=deck.title,
        total_cards=total_cards,
        distinct_cards=distinct_cards,
        type_distribution=[
            DistributionEntry(label=k, count=v)
            for k, v in sorted(type_counter.items(), key=lambda x: -x[1])
        ],
        attribute_distribution=[
            DistributionEntry(label=k, count=v)
            for k, v in sorted(attr_counter.items(), key=lambda x: -x[1])
        ],
        level_distribution=[
            LevelEntry(level=k, count=v)
            for k, v in sorted(level_counter.items())
        ],
        frame_distribution=[
            DistributionEntry(label=k, count=v)
            for k, v in sorted(frame_counter.items(), key=lambda x: -x[1])
        ],
    )


async def get_archetype_analytics(archetype_label: str, db: AsyncSession) -> ArchetypeAnalyticsOut | None:
    rows = await db.execute(
        select(Deck).where(Deck.archetype_label == archetype_label)
    )
    decks = list(rows.scalars())
    if not decks:
        return None

    deck_count = len(decks)
    card_deck_counts: dict[int, int] = defaultdict(int)
    card_total_qty: dict[int, float] = defaultdict(float)
    card_meta: dict[int, Card] = {}

    main_totals: list[int] = []
    extra_totals: list[int] = []
    side_totals: list[int] = []
    monthly: dict[str, int] = defaultdict(int)

    for deck in decks:
        submission = await _get_submission(deck.id, db)
        if not submission:
            continue

        # Monthly submissions (by deck submission date)
        if submission.created_at:
            month_key = submission.created_at.strftime("%Y-%m")
            monthly[month_key] += 1

        deck_cards: list[DeckCard] = submission.cards
        seen_in_deck: set[int] = set()

        main_qty = extra_qty = side_qty = 0

        for dc in deck_cards:
            card: Card = dc.card
            card_meta[card.id] = card

            if card.id not in seen_in_deck:
                card_deck_counts[card.id] += 1
                seen_in_deck.add(card.id)
            card_total_qty[card.id] += dc.quantity

            if dc.section == CardSection.main:
                main_qty += dc.quantity
            elif dc.section == CardSection.extra:
                extra_qty += dc.quantity
            elif dc.section == CardSection.side:
                side_qty += dc.quantity

        main_totals.append(main_qty)
        extra_totals.append(extra_qty)
        side_totals.append(side_qty)

    def _avg(lst: list[int]) -> float:
        return round(sum(lst) / len(lst), 1) if lst else 0.0

    core: list[CardFrequency] = []
    flex: list[CardFrequency] = []
    tech: list[CardFrequency] = []

    for card_id, deck_cnt in sorted(card_deck_counts.items(), key=lambda x: -x[1]):
        freq = deck_cnt / deck_count
        avg_qty = card_total_qty[card_id] / deck_cnt
        card = card_meta[card_id]
        entry = CardFrequency(
            card_id=card_id,
            name=card.name,
            image_url=f"/api/v1/cards/{card_id}/image",
            type_label=_main_type(card.type),
            frame_type=card.frame_type or "effect",
            deck_count=deck_cnt,
            frequency=round(freq, 3),
            avg_quantity=round(avg_qty, 2),
        )
        if freq >= 0.75:
            core.append(entry)
        elif freq >= 0.25:
            flex.append(entry)
        else:
            tech.append(entry)

    return ArchetypeAnalyticsOut(
        archetype_label=archetype_label,
        deck_count=deck_count,
        avg_main_count=_avg(main_totals),
        avg_extra_count=_avg(extra_totals),
        avg_side_count=_avg(side_totals),
        core_cards=core,
        flex_cards=flex,
        tech_cards=tech,
        monthly_submissions=[
            MonthlyEntry(month=k, count=v)
            for k, v in sorted(monthly.items())
        ],
    )


async def get_overview(db: AsyncSession) -> OverviewOut:
    total_decks = await db.scalar(select(func.count(Deck.id))) or 0
    total_cards = await db.scalar(select(func.count(Card.id))) or 0
    distinct_archetypes = await db.scalar(
        select(func.count(func.distinct(Deck.archetype_label)))
        .where(Deck.archetype_label.isnot(None))
    ) or 0

    archetype_rows = await db.execute(
        select(Deck.archetype_label, func.count(Deck.id).label("cnt"))
        .where(Deck.archetype_label.isnot(None))
        .group_by(Deck.archetype_label)
        .order_by(func.count(Deck.id).desc())
        .limit(10)
    )

    return OverviewOut(
        total_decks=total_decks,
        total_cards_in_db=total_cards,
        total_archetypes=distinct_archetypes,
        top_archetypes=[
            TopArchetype(label=row.archetype_label, deck_count=row.cnt)
            for row in archetype_rows.all()
        ],
    )
