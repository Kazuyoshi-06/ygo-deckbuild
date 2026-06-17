from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Card, Deck, DeckCard, DeckSubmission
from app.models.enums import CardSection
from app.schemas.analytics import (
    ArchetypeAnalyticsOut,
    ArchetypeCompareOut,
    ArchetypeCompareSummary,
    CardFrequency,
    CommonCardEntry,
    DeckAnalyticsOut,
    DistributionEntry,
    LevelEntry,
    MetaWinShareEntry,
    MetaWinShareOut,
    MonthlyEntry,
    OcgToTcgEntry,
    OcgToTcgPipelineOut,
    OverviewOut,
    TechSuggestionsOut,
    TopArchetype,
    TrendingArchetypeEntry,
    TrendingArchetypesOut,
)
from app.schemas.evolution import CardTrend, EvolutionOut

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


class _ArchetypeFrequencies:
    def __init__(
        self,
        deck_count: int,
        core: list[CardFrequency],
        flex: list[CardFrequency],
        tech: list[CardFrequency],
        avg_main_count: float,
        avg_extra_count: float,
        avg_side_count: float,
        monthly_submissions: list[MonthlyEntry],
    ) -> None:
        self.deck_count = deck_count
        self.core = core
        self.flex = flex
        self.tech = tech
        self.avg_main_count = avg_main_count
        self.avg_extra_count = avg_extra_count
        self.avg_side_count = avg_side_count
        self.monthly_submissions = monthly_submissions


async def _compute_archetype_frequencies(
    archetype_label: str, db: AsyncSession
) -> _ArchetypeFrequencies | None:
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

    return _ArchetypeFrequencies(
        deck_count=deck_count,
        core=core,
        flex=flex,
        tech=tech,
        avg_main_count=_avg(main_totals),
        avg_extra_count=_avg(extra_totals),
        avg_side_count=_avg(side_totals),
        monthly_submissions=[
            MonthlyEntry(month=k, count=v)
            for k, v in sorted(monthly.items())
        ],
    )


async def get_archetype_analytics(archetype_label: str, db: AsyncSession) -> ArchetypeAnalyticsOut | None:
    freq = await _compute_archetype_frequencies(archetype_label, db)
    if freq is None:
        return None
    return ArchetypeAnalyticsOut(
        archetype_label=archetype_label,
        deck_count=freq.deck_count,
        avg_main_count=freq.avg_main_count,
        avg_extra_count=freq.avg_extra_count,
        avg_side_count=freq.avg_side_count,
        core_cards=freq.core,
        flex_cards=freq.flex,
        tech_cards=freq.tech,
        monthly_submissions=freq.monthly_submissions,
    )


async def get_archetype_tech_suggestions(
    archetype_label: str, db: AsyncSession, limit: int = 10
) -> TechSuggestionsOut | None:
    """Top tech cards (frequency < 25%) for an archetype, for builder suggestions."""
    freq = await _compute_archetype_frequencies(archetype_label, db)
    if freq is None:
        return None
    return TechSuggestionsOut(
        archetype_label=archetype_label,
        deck_count=freq.deck_count,
        cards=freq.tech[:limit],
    )


def _detect_trend(monthly: list[float]) -> tuple[str, float]:
    """Slope-based trend from last 3 data points. Returns (label, slope_per_month)."""
    if len(monthly) < 2:
        return "stable", 0.0
    recent = monthly[-3:]
    slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
    if slope > 0.10:
        return "rising_strong", round(slope, 4)
    if slope > 0.04:
        return "rising", round(slope, 4)
    if slope < -0.10:
        return "falling_strong", round(slope, 4)
    if slope < -0.04:
        return "falling", round(slope, 4)
    return "stable", round(slope, 4)


_TREND_ORDER = {"rising_strong": 0, "rising": 1, "stable": 2, "falling": 3, "falling_strong": 4}

_EVOLUTION_SQL = text("""
    WITH latest_subs AS (
        SELECT DISTINCT ON (ds.deck_id)
            ds.id          AS sub_id,
            ds.deck_id,
            TO_CHAR(
                DATE_TRUNC('month',
                    COALESCE(ds.event_date, ds.created_at::date)
                ), 'YYYY-MM'
            ) AS month
        FROM deck_submissions ds
        JOIN decks d ON d.id = ds.deck_id
        WHERE d.archetype_label = :label
          AND COALESCE(ds.event_date, ds.created_at::date)
              >= (CURRENT_DATE - (:months * INTERVAL '1 month'))
        ORDER BY ds.deck_id, ds.created_at DESC
    ),
    monthly_totals AS (
        SELECT month, COUNT(*) AS deck_count
        FROM latest_subs
        GROUP BY month
    ),
    card_monthly AS (
        SELECT
            ls.month,
            dc.card_id,
            c.name        AS card_name,
            c.frame_type,
            COUNT(DISTINCT ls.deck_id) AS decks_with_card
        FROM latest_subs ls
        JOIN deck_cards dc ON dc.deck_submission_id = ls.sub_id
        JOIN cards c      ON c.id = dc.card_id
        GROUP BY ls.month, dc.card_id, c.name, c.frame_type
    )
    SELECT
        cm.month,
        mt.deck_count,
        cm.card_id,
        cm.card_name,
        cm.frame_type,
        ROUND(cm.decks_with_card::numeric / mt.deck_count, 4) AS presence_pct
    FROM card_monthly cm
    JOIN monthly_totals mt ON mt.month = cm.month
    ORDER BY cm.month, presence_pct DESC
""")


async def get_archetype_evolution(archetype_label: str, months: int, db: AsyncSession) -> EvolutionOut:
    """Monthly card-presence evolution for an archetype."""
    rows = (await db.execute(_EVOLUTION_SQL, {"label": archetype_label, "months": months})).fetchall()

    if not rows:
        return EvolutionOut(
            archetype_label=archetype_label,
            months=[],
            deck_counts=[],
            total_decks=0,
            cards=[],
            has_data=False,
        )

    month_deck: dict[str, int] = {}
    card_data: dict[int, dict] = {}

    for row in rows:
        m = row.month
        if m not in month_deck:
            month_deck[m] = int(row.deck_count)
        cid = int(row.card_id)
        if cid not in card_data:
            card_data[cid] = {"name": row.card_name, "frame_type": row.frame_type or "", "monthly": {}}
        card_data[cid]["monthly"][m] = float(row.presence_pct)

    sorted_months = sorted(month_deck.keys())
    deck_counts = [month_deck[m] for m in sorted_months]
    total_decks = sum(deck_counts)

    card_trends: list[CardTrend] = []
    for cid, info in card_data.items():
        monthly_presence = [info["monthly"].get(m, 0.0) for m in sorted_months]
        avg = sum(monthly_presence) / len(monthly_presence)
        peak = max(monthly_presence)
        months_present = sum(1 for p in monthly_presence if p > 0)

        if avg < 0.05 and peak < 0.20:
            continue
        if months_present < 2 and len(sorted_months) > 2:
            continue

        trend_label, slope = _detect_trend(monthly_presence)
        card_trends.append(CardTrend(
            card_id=cid,
            name=info["name"],
            frame_type=info["frame_type"],
            monthly_presence=[round(p, 4) for p in monthly_presence],
            trend=trend_label,
            slope=slope,
            avg_presence=round(avg, 4),
            peak_presence=round(peak, 4),
        ))

    card_trends.sort(key=lambda c: (_TREND_ORDER[c.trend], -c.avg_presence))

    return EvolutionOut(
        archetype_label=archetype_label,
        months=sorted_months,
        deck_counts=deck_counts,
        total_decks=total_decks,
        cards=card_trends,
        has_data=True,
    )


async def get_archetype_comparison(
    labels: list[str], db: AsyncSession, months: int = 12
) -> ArchetypeCompareOut | None:
    """Side-by-side comparison of 2+ archetypes: meta share, common/exclusive cards, evolution."""
    freqs: dict[str, _ArchetypeFrequencies] = {}
    for label in labels:
        freq = await _compute_archetype_frequencies(label, db)
        if freq is None:
            return None
        freqs[label] = freq

    total_decks = await db.scalar(select(func.count(Deck.id))) or 0

    summaries: list[ArchetypeCompareSummary] = []
    notable_by_label: dict[str, dict[int, CardFrequency]] = {}
    for label in labels:
        freq = freqs[label]
        notable = freq.core + freq.flex
        notable_by_label[label] = {c.card_id: c for c in notable}
        top_cards = sorted(notable, key=lambda c: -c.frequency)[:15]
        summaries.append(ArchetypeCompareSummary(
            label=label,
            deck_count=freq.deck_count,
            meta_share=round(freq.deck_count / total_decks, 4) if total_decks else 0.0,
            avg_main_count=freq.avg_main_count,
            avg_extra_count=freq.avg_extra_count,
            avg_side_count=freq.avg_side_count,
            top_cards=top_cards,
        ))

    common_ids = set.intersection(*(set(m.keys()) for m in notable_by_label.values()))
    common_cards: list[CommonCardEntry] = []
    for cid in common_ids:
        ref = notable_by_label[labels[0]][cid]
        common_cards.append(CommonCardEntry(
            card_id=cid,
            name=ref.name,
            image_url=ref.image_url,
            type_label=ref.type_label,
            frame_type=ref.frame_type,
            frequencies={label: notable_by_label[label][cid].frequency for label in labels},
        ))
    common_cards.sort(key=lambda c: -max(c.frequencies.values()))

    # Cards notable in exactly one archetype, and entirely absent (incl. tech) from the others
    all_card_ids_by_label = {
        label: {c.card_id for c in freqs[label].core + freqs[label].flex + freqs[label].tech}
        for label in labels
    }
    exclusive_cards: dict[str, list[CardFrequency]] = {}
    for label in labels:
        others_ids: set[int] = set()
        for other in labels:
            if other != label:
                others_ids |= all_card_ids_by_label[other]
        exclusive = [c for c in notable_by_label[label].values() if c.card_id not in others_ids]
        exclusive.sort(key=lambda c: -c.frequency)
        exclusive_cards[label] = exclusive

    evolution: dict[str, EvolutionOut] = {}
    for label in labels:
        evolution[label] = await get_archetype_evolution(label, months, db)

    return ArchetypeCompareOut(
        archetypes=summaries,
        common_cards=common_cards,
        exclusive_cards=exclusive_cards,
        evolution=evolution,
    )


_TRENDING_SQL = text("""
    WITH weekly AS (
        SELECT
            d.archetype_label AS label,
            TO_CHAR(DATE_TRUNC('week', COALESCE(ds.event_date, ds.created_at::date)), 'IYYY-IW') AS week,
            COUNT(*) AS cnt
        FROM deck_submissions ds
        JOIN decks d ON d.id = ds.deck_id
        WHERE d.archetype_label IS NOT NULL
          AND COALESCE(ds.event_date, ds.created_at::date) >= (CURRENT_DATE - (:weeks * INTERVAL '1 week'))
        GROUP BY d.archetype_label, week
    ),
    weekly_totals AS (
        SELECT week, SUM(cnt) AS total FROM weekly GROUP BY week
    )
    SELECT w.label, w.week, w.cnt, wt.total
    FROM weekly w
    JOIN weekly_totals wt ON wt.week = w.week
    ORDER BY w.label, w.week
""")


async def get_trending_archetypes(
    db: AsyncSession, weeks: int = 6, limit: int = 5
) -> TrendingArchetypesOut:
    """Archetypes rising/falling in meta share over the recent weeks (slope logic from D5's evolution)."""
    rows = (await db.execute(_TRENDING_SQL, {"weeks": weeks})).fetchall()

    if not rows:
        return TrendingArchetypesOut(weeks_analyzed=weeks, rising=[], falling=[], has_data=False)

    week_keys: list[str] = sorted({row.week for row in rows})
    label_data: dict[str, dict] = {}
    for row in rows:
        info = label_data.setdefault(row.label, {"weekly": {}, "deck_count": 0})
        share = float(row.cnt) / float(row.total) if row.total else 0.0
        info["weekly"][row.week] = share
        info["deck_count"] += int(row.cnt)

    entries: list[TrendingArchetypeEntry] = []
    for label, info in label_data.items():
        weekly_shares = [info["weekly"].get(w, 0.0) for w in week_keys]
        trend_label, slope = _detect_trend(weekly_shares)
        if trend_label == "stable":
            continue
        entries.append(TrendingArchetypeEntry(
            label=label,
            trend=trend_label,
            slope=slope,
            current_share=round(weekly_shares[-1], 4),
            deck_count=info["deck_count"],
        ))

    rising = sorted(
        (e for e in entries if e.trend in ("rising", "rising_strong")),
        key=lambda e: -e.slope,
    )[:limit]
    falling = sorted(
        (e for e in entries if e.trend in ("falling", "falling_strong")),
        key=lambda e: e.slope,
    )[:limit]

    return TrendingArchetypesOut(weeks_analyzed=weeks, rising=rising, falling=falling, has_data=True)


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


_TOP8_THRESHOLD = 8


async def get_meta_vs_win_share(db: AsyncSession) -> MetaWinShareOut:
    """Meta share (presence across all placed submissions) vs win share (presence in top 8)."""
    rows = (await db.execute(
        select(Deck.archetype_label, DeckSubmission.placement)
        .join(DeckSubmission, DeckSubmission.deck_id == Deck.id)
        .where(DeckSubmission.placement.isnot(None))
        .where(Deck.archetype_label.isnot(None))
    )).all()

    total_placed = len(rows)
    total_top8 = sum(1 for _, placement in rows if placement <= _TOP8_THRESHOLD)

    counts: dict[str, int] = defaultdict(int)
    top8_counts: dict[str, int] = defaultdict(int)
    for label, placement in rows:
        counts[label] += 1
        if placement <= _TOP8_THRESHOLD:
            top8_counts[label] += 1

    entries = [
        MetaWinShareEntry(
            label=label,
            total_count=counts[label],
            top8_count=top8_counts[label],
            meta_share=round(counts[label] / total_placed, 4) if total_placed else 0.0,
            win_share=round(top8_counts[label] / total_top8, 4) if total_top8 else 0.0,
        )
        for label in counts
    ]
    entries.sort(key=lambda e: (-e.win_share, -e.meta_share))

    return MetaWinShareOut(
        total_placed_submissions=total_placed,
        total_top8_submissions=total_top8,
        entries=entries,
        has_data=total_placed > 0,
    )


_OCG_TCG_RELEASE_SQL = text("""
    SELECT archetype,
           MIN(ocg_date) AS ocg_release,
           MIN(tcg_date) AS tcg_release,
           COUNT(*) AS card_count
    FROM cards
    WHERE archetype IS NOT NULL AND archetype != ''
    GROUP BY archetype
    HAVING COUNT(*) >= :min_cards
""")


async def get_ocg_to_tcg_pipeline(db: AsyncSession, min_cards: int = 3) -> OcgToTcgPipelineOut:
    """OCG-exclusive archetypes with a predicted TCG arrival, based on the historical average release gap."""
    rows = (await db.execute(_OCG_TCG_RELEASE_SQL, {"min_cards": min_cards})).all()

    gaps_days: list[int] = []
    pending_rows = []
    for row in rows:
        if row.ocg_release and row.tcg_release:
            gap = (row.tcg_release - row.ocg_release).days
            if gap > 0:
                gaps_days.append(gap)
        elif row.ocg_release and not row.tcg_release:
            pending_rows.append(row)

    avg_gap_days = sum(gaps_days) / len(gaps_days) if gaps_days else None

    pending = [
        OcgToTcgEntry(
            archetype=row.archetype,
            ocg_release_date=row.ocg_release,
            card_count=row.card_count,
            predicted_tcg_date=(
                row.ocg_release + timedelta(days=avg_gap_days) if avg_gap_days is not None else None
            ),
        )
        for row in pending_rows
    ]
    pending.sort(key=lambda e: e.ocg_release_date, reverse=True)

    return OcgToTcgPipelineOut(
        avg_gap_days=round(avg_gap_days, 1) if avg_gap_days is not None else None,
        sample_size=len(gaps_days),
        pending=pending,
        has_data=len(pending) > 0,
    )
