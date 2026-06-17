from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.banlist import BanlistPredictionOut, BanlistRiskEntry

DISCLAIMER = (
    "Heuristic estimate only, based on this database's deck pool and banlist history — "
    "not an official prediction. Treat as a rough signal, not a guarantee."
)

_RECENT_WINDOW_DAYS = 365
_MIN_RISK_SCORE = 0.15
_MAX_CANDIDATES = 20

_CANDIDATES_SQL = text("""
    WITH played AS (
        SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id, ds.deck_id
        FROM deck_submissions ds
        ORDER BY ds.deck_id, ds.created_at DESC
    ),
    total AS (SELECT COUNT(*) AS n FROM played),
    card_play AS (
        SELECT dc.card_id, COUNT(DISTINCT p.deck_id) AS deck_count
        FROM played p
        JOIN deck_cards dc ON dc.deck_submission_id = p.sub_id
        GROUP BY dc.card_id
    ),
    latest_banlist AS (
        SELECT id FROM banlists WHERE format = :fmt ORDER BY effective_date DESC LIMIT 1
    ),
    currently_restricted AS (
        SELECT card_id FROM banlist_entries WHERE banlist_id IN (SELECT id FROM latest_banlist)
    ),
    prior_hits AS (
        SELECT be.card_id, COUNT(*) AS hit_count
        FROM banlist_entries be
        JOIN banlists b ON b.id = be.banlist_id
        WHERE b.format = :fmt
        GROUP BY be.card_id
    )
    SELECT
        cp.card_id, c.name, c.archetype, c.frame_type, c.tcg_date, c.ocg_date,
        cp.deck_count, t.n AS total_decks,
        COALESCE(ph.hit_count, 0) AS prior_hits
    FROM card_play cp
    JOIN cards c ON c.id = cp.card_id
    CROSS JOIN total t
    LEFT JOIN prior_hits ph ON ph.card_id = cp.card_id
    WHERE cp.card_id NOT IN (SELECT card_id FROM currently_restricted)
    ORDER BY cp.deck_count DESC
""")

_RISK_LABELS = [
    (0.6, "Very High"),
    (0.4, "High"),
    (0.2, "Moderate"),
]


def _risk_label(score: float) -> str:
    for threshold, label in _RISK_LABELS:
        if score >= threshold:
            return label
    return "Low"


async def get_banlist_prediction(db: AsyncSession, fmt: str) -> BanlistPredictionOut:
    """Heuristic banlist-risk score: blends deck play rate, recency, and historical hit count."""
    rows = (await db.execute(_CANDIDATES_SQL, {"fmt": fmt})).all()

    total_decks = int(rows[0].total_decks) if rows else 0
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=_RECENT_WINDOW_DAYS)

    candidates: list[BanlistRiskEntry] = []
    for row in rows:
        play_rate = row.deck_count / total_decks if total_decks else 0.0

        release_date = row.tcg_date if fmt == "TCG" else row.ocg_date
        is_recent = bool(release_date and release_date.replace(tzinfo=timezone.utc) >= recent_cutoff)

        hit_factor = min(row.prior_hits / 3, 1.0)
        score = round(0.55 * play_rate + 0.20 * (1.0 if is_recent else 0.0) + 0.25 * hit_factor, 4)

        if score < _MIN_RISK_SCORE:
            continue

        candidates.append(BanlistRiskEntry(
            card_id=row.card_id,
            name=row.name,
            image_url=f"/api/v1/cards/{row.card_id}/image",
            archetype=row.archetype,
            frame_type=row.frame_type or "effect",
            play_rate=round(play_rate, 4),
            deck_count=row.deck_count,
            is_recent=is_recent,
            prior_hits=row.prior_hits,
            risk_score=score,
            risk_label=_risk_label(score),
        ))

    candidates.sort(key=lambda c: -c.risk_score)

    return BanlistPredictionOut(
        format=fmt,
        total_decks_analyzed=total_decks,
        candidates=candidates[:_MAX_CANDIDATES],
        has_data=len(candidates) > 0,
        disclaimer=DISCLAIMER,
    )
