from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card
from app.models.banlist import Banlist, BanlistEntry
from app.models.enums import BanlistStatus
from app.schemas.banlist import CardReplacementsOut, ReplacementCandidate

_MIN_DELTA = 0.05  # ignore noise: require at least +5pp presence increase to count as a "replacement"

_REPLACEMENT_SQL = text("""
    WITH affected_archetypes AS (
        SELECT DISTINCT d.archetype_label
        FROM deck_submissions ds
        JOIN decks d ON d.id = ds.deck_id
        JOIN deck_cards dc ON dc.deck_submission_id = ds.id
        WHERE dc.card_id = :card_id
          AND d.archetype_label IS NOT NULL
          AND COALESCE(ds.event_date, ds.created_at::date) < :ban_date
    ),
    before_subs AS (
        SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id, ds.deck_id
        FROM deck_submissions ds
        JOIN decks d ON d.id = ds.deck_id
        JOIN affected_archetypes aa ON aa.archetype_label = d.archetype_label
        WHERE COALESCE(ds.event_date, ds.created_at::date) < :ban_date
        ORDER BY ds.deck_id, ds.created_at DESC
    ),
    after_subs AS (
        SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id, ds.deck_id
        FROM deck_submissions ds
        JOIN decks d ON d.id = ds.deck_id
        JOIN affected_archetypes aa ON aa.archetype_label = d.archetype_label
        WHERE COALESCE(ds.event_date, ds.created_at::date) >= :ban_date
        ORDER BY ds.deck_id, ds.created_at DESC
    ),
    before_total AS (SELECT COUNT(*) AS n FROM before_subs),
    after_total AS (SELECT COUNT(*) AS n FROM after_subs),
    before_freq AS (
        SELECT dc.card_id, COUNT(DISTINCT bs.deck_id) AS cnt
        FROM before_subs bs
        JOIN deck_cards dc ON dc.deck_submission_id = bs.sub_id
        GROUP BY dc.card_id
    ),
    after_freq AS (
        SELECT dc.card_id, COUNT(DISTINCT asub.deck_id) AS cnt
        FROM after_subs asub
        JOIN deck_cards dc ON dc.deck_submission_id = asub.sub_id
        GROUP BY dc.card_id
    )
    SELECT
        COALESCE(bf.card_id, af.card_id) AS card_id,
        c.name, c.frame_type,
        CASE WHEN bt.n = 0 THEN 0 ELSE COALESCE(bf.cnt, 0)::numeric / bt.n END AS before_pct,
        CASE WHEN at.n = 0 THEN 0 ELSE COALESCE(af.cnt, 0)::numeric / at.n END AS after_pct,
        bt.n AS before_total,
        at.n AS after_total
    FROM before_freq bf
    FULL OUTER JOIN after_freq af ON af.card_id = bf.card_id
    JOIN cards c ON c.id = COALESCE(bf.card_id, af.card_id)
    CROSS JOIN before_total bt
    CROSS JOIN after_total at
""")


async def _find_ban_date(db: AsyncSession, card_id: int, fmt: str) -> date | None:
    """Effective date the card most recently became forbidden in `fmt`, if it's still forbidden now."""
    rows = (await db.execute(
        text("""
            SELECT b.effective_date, be.status
            FROM banlists b
            LEFT JOIN banlist_entries be ON be.banlist_id = b.id AND be.card_id = :card_id
            WHERE b.format = :fmt
            ORDER BY b.effective_date DESC
        """),
        {"card_id": card_id, "fmt": fmt},
    )).all()

    if not rows or rows[0].status != BanlistStatus.forbidden.value:
        return None

    ban_date = rows[0].effective_date
    for row in rows[1:]:
        if row.status == BanlistStatus.forbidden.value:
            ban_date = row.effective_date
        else:
            break
    return ban_date


async def get_card_replacements(card_id: int, fmt: str, db: AsyncSession) -> CardReplacementsOut | None:
    """For a currently-forbidden card, find cards that replaced it in affected archetypes after the ban."""
    card = await db.get(Card, card_id)
    if not card:
        return None

    ban_date = await _find_ban_date(db, card_id, fmt)
    if ban_date is None:
        return CardReplacementsOut(
            card_id=card_id,
            card_name=card.name,
            format=fmt,
            is_banned=False,
            affected_archetypes=[],
            before_deck_count=0,
            after_deck_count=0,
            replacements=[],
            has_data=False,
        )

    archetype_rows = (await db.execute(
        text("""
            SELECT DISTINCT d.archetype_label
            FROM deck_submissions ds
            JOIN decks d ON d.id = ds.deck_id
            JOIN deck_cards dc ON dc.deck_submission_id = ds.id
            WHERE dc.card_id = :card_id
              AND d.archetype_label IS NOT NULL
              AND COALESCE(ds.event_date, ds.created_at::date) < :ban_date
        """),
        {"card_id": card_id, "ban_date": ban_date},
    )).all()
    affected_archetypes = sorted(row.archetype_label for row in archetype_rows)

    if not affected_archetypes:
        return CardReplacementsOut(
            card_id=card_id,
            card_name=card.name,
            format=fmt,
            is_banned=True,
            ban_date=ban_date,
            affected_archetypes=[],
            before_deck_count=0,
            after_deck_count=0,
            replacements=[],
            has_data=False,
        )

    rows = (await db.execute(_REPLACEMENT_SQL, {"card_id": card_id, "ban_date": ban_date})).all()

    before_total = int(rows[0].before_total) if rows else 0
    after_total = int(rows[0].after_total) if rows else 0

    candidates: list[ReplacementCandidate] = []
    for row in rows:
        if int(row.card_id) == card_id:
            continue
        before_pct = float(row.before_pct)
        after_pct = float(row.after_pct)
        delta = after_pct - before_pct
        if delta < _MIN_DELTA:
            continue
        candidates.append(ReplacementCandidate(
            card_id=int(row.card_id),
            name=row.name,
            image_url=f"/api/v1/cards/{int(row.card_id)}/image",
            frame_type=row.frame_type or "effect",
            before_pct=round(before_pct, 4),
            after_pct=round(after_pct, 4),
            delta=round(delta, 4),
        ))

    candidates.sort(key=lambda c: -c.delta)

    return CardReplacementsOut(
        card_id=card_id,
        card_name=card.name,
        format=fmt,
        is_banned=True,
        ban_date=ban_date,
        affected_archetypes=affected_archetypes,
        before_deck_count=before_total,
        after_deck_count=after_total,
        replacements=candidates[:10],
        has_data=after_total > 0,
    )
