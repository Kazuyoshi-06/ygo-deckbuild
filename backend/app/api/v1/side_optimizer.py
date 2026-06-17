from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.side_optimizer import SideCardInfo, SideOptimizerOut
from app.services import cache_service
from app.services.side_optimizer_service import get_archetype_side_matrix

router = APIRouter(tags=["side-optimizer"])

_IMG = "/api/v1/cards/{card_id}/image"


@router.get("/{deck_id}/side-optimizer", response_model=SideOptimizerOut)
async def side_optimizer(
    deck_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> SideOptimizerOut | Response:
    """Cached for 5 minutes (T3.7) — invalidated whenever a deck is imported."""
    cached = await cache_service.get_cached(request)
    if cached is not None:
        return Response(content=cached, media_type="application/json")

    # ── Latest submission ────────────────────────────────────────────────
    sub_row = await db.execute(
        text(
            "SELECT ds.id, d.title "
            "FROM deck_submissions ds "
            "JOIN decks d ON d.id = ds.deck_id "
            "WHERE ds.deck_id = :did "
            "ORDER BY ds.created_at DESC LIMIT 1"
        ),
        {"did": deck_id},
    )
    sub = sub_row.mappings().first()
    if not sub:
        raise HTTPException(404, "Deck not found")

    sub_id: int = sub["id"]
    deck_title: str = sub["title"]

    # ── Current side deck ────────────────────────────────────────────────
    side_rows = await db.execute(
        text(
            "SELECT dc.card_id, c.name, c.frame_type, "
            "  SUM(dc.quantity) AS quantity, "
            "  MAX(dc.role) AS role "
            "FROM deck_cards dc "
            "JOIN cards c ON c.id = dc.card_id "
            "WHERE dc.deck_submission_id = :sid AND dc.section = 'side' "
            "GROUP BY dc.card_id, c.name, c.frame_type"
        ),
        {"sid": sub_id},
    )
    side_cards = [dict(r) for r in side_rows.mappings().all()]
    side_count = sum(r["quantity"] for r in side_cards)
    side_card_ids = {r["card_id"] for r in side_cards}

    # ── Global side popularity (other decks) ─────────────────────────────
    pop_rows = await db.execute(
        text(
            """
            WITH other_subs AS (
                SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id, ds.deck_id
                FROM deck_submissions ds
                WHERE ds.deck_id != :did
                ORDER BY ds.deck_id, ds.created_at DESC
            ),
            total AS (SELECT COUNT(*) AS n FROM other_subs),
            side_presence AS (
                SELECT dc.card_id, COUNT(DISTINCT os.deck_id) AS cnt
                FROM other_subs os
                JOIN deck_cards dc ON dc.deck_submission_id = os.sub_id
                  AND dc.section = 'side'
                GROUP BY dc.card_id
            )
            SELECT
                sp.card_id,
                c.name,
                c.frame_type,
                sp.cnt,
                t.n AS total,
                CASE WHEN t.n = 0 THEN 0
                     ELSE ROUND(sp.cnt::numeric / t.n, 4)
                END AS side_pct
            FROM side_presence sp
            JOIN cards c ON c.id = sp.card_id
            CROSS JOIN total t
            ORDER BY side_pct DESC
            """
        ),
        {"did": deck_id},
    )
    pop_all = pop_rows.mappings().all()

    total_other_decks = int(pop_all[0]["total"]) if pop_all else 0
    has_side_data = total_other_decks > 0
    pop_map: dict[int, float] = {r["card_id"]: float(r["side_pct"]) for r in pop_all}

    current_side: list[SideCardInfo] = [
        SideCardInfo(
            card_id=r["card_id"],
            name=r["name"],
            frame_type=r["frame_type"],
            image_url=_IMG.format(card_id=r["card_id"]),
            quantity=int(r["quantity"]),
            role=r["role"],
            global_side_pct=pop_map.get(r["card_id"], 0.0),
        )
        for r in side_cards
    ]

    suggestions: list[SideCardInfo] = []
    for r in pop_all:
        if r["card_id"] in side_card_ids:
            continue
        suggestions.append(
            SideCardInfo(
                card_id=r["card_id"],
                name=r["name"],
                frame_type=r["frame_type"],
                image_url=_IMG.format(card_id=r["card_id"]),
                quantity=0,
                role=None,
                global_side_pct=float(r["side_pct"]),
            )
        )
        if len(suggestions) >= 25:
            break

    # ── Archetype × side-card matrix ─────────────────────────────────────
    archetypes = await get_archetype_side_matrix(db, exclude_deck_id=deck_id, top_n=15)

    result = SideOptimizerOut(
        deck_id=deck_id,
        deck_title=deck_title,
        side_count=side_count,
        current_side=current_side,
        suggestions=suggestions,
        total_other_decks=total_other_decks,
        has_side_data=has_side_data,
        archetypes=archetypes,
    )
    await cache_service.set_cached(request, result.model_dump_json())
    return result
