from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analytics import ArchetypeAnalyticsOut, DeckAnalyticsOut, OverviewOut
from app.schemas.evolution import CardTrend, EvolutionOut
from app.services import analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/overview", response_model=OverviewOut)
async def overview(db: AsyncSession = Depends(get_db)) -> OverviewOut:
    return await analytics_service.get_overview(db)


@router.get("/decks/{deck_id}", response_model=DeckAnalyticsOut)
async def deck_analytics(deck_id: int, db: AsyncSession = Depends(get_db)) -> DeckAnalyticsOut:
    result = await analytics_service.get_deck_analytics(deck_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return result


@router.get("/archetypes/{archetype_label}", response_model=ArchetypeAnalyticsOut)
async def archetype_analytics(
    archetype_label: str,
    db: AsyncSession = Depends(get_db),
) -> ArchetypeAnalyticsOut:
    result = await analytics_service.get_archetype_analytics(archetype_label, db)
    if result is None:
        raise HTTPException(status_code=404, detail="No decks found for this archetype")
    return result


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


@router.get("/archetypes/{archetype_label}/evolution", response_model=EvolutionOut)
async def archetype_evolution(
    archetype_label: str,
    months: int = Query(default=12, ge=2, le=24, description="Number of months to look back"),
    db: AsyncSession = Depends(get_db),
) -> EvolutionOut:
    """Monthly card-presence evolution for an archetype."""
    sql = text("""
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

    rows = (await db.execute(sql, {"label": archetype_label, "months": months})).fetchall()

    if not rows:
        return EvolutionOut(
            archetype_label=archetype_label,
            months=[],
            deck_counts=[],
            total_decks=0,
            cards=[],
            has_data=False,
        )

    # Pivot: month_order, deck_counts, card data
    month_deck: dict[str, int] = {}
    # card_id → {name, frame_type, month → presence}
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

    # Build CardTrend entries; filter noise
    card_trends: list[CardTrend] = []
    for cid, info in card_data.items():
        monthly_presence = [info["monthly"].get(m, 0.0) for m in sorted_months]
        avg = sum(monthly_presence) / len(monthly_presence)
        peak = max(monthly_presence)
        months_present = sum(1 for p in monthly_presence if p > 0)

        # Keep cards with meaningful presence
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
