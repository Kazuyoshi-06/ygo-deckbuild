from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.side_optimizer import (
    ArchetypeSideCard,
    ArchetypeSideData,
    SideCardInfo,
    SideOptimizerOut,
)

router = APIRouter(tags=["side-optimizer"])

_IMG_BASE = "/api/v1/cards/{card_id}/image"


@router.get("/{deck_id}/side-optimizer", response_model=SideOptimizerOut)
async def side_optimizer(deck_id: int, db: AsyncSession = Depends(get_db)):
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
            "  COALESCE(ci.image_url, '') AS image_url, "
            "  SUM(dc.quantity) AS quantity, "
            "  MAX(dc.role) AS role "
            "FROM deck_cards dc "
            "JOIN cards c ON c.id = dc.card_id "
            "LEFT JOIN card_images ci ON ci.card_id = dc.card_id "
            "WHERE dc.deck_submission_id = :sid AND dc.section = 'side' "
            "GROUP BY dc.card_id, c.name, c.frame_type, ci.image_url"
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
                COALESCE(ci.image_url, '') AS image_url,
                sp.cnt,
                t.n AS total,
                CASE WHEN t.n = 0 THEN 0
                     ELSE ROUND(sp.cnt::numeric / t.n, 4)
                END AS side_pct
            FROM side_presence sp
            JOIN cards c ON c.id = sp.card_id
            LEFT JOIN card_images ci ON ci.card_id = sp.card_id
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
            image_url=r["image_url"] or _IMG_BASE.format(card_id=r["card_id"]),
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
                image_url=r["image_url"] or _IMG_BASE.format(card_id=r["card_id"]),
                quantity=0,
                role=None,
                global_side_pct=float(r["side_pct"]),
            )
        )
        if len(suggestions) >= 25:
            break

    # ── Archetype × side-card matrix ─────────────────────────────────────
    arch_rows = await db.execute(
        text(
            """
            WITH other_subs AS (
                SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id,
                       ds.deck_id, d.archetype_label
                FROM deck_submissions ds
                JOIN decks d ON d.id = ds.deck_id
                WHERE d.archetype_label IS NOT NULL
                  AND ds.deck_id != :did
                ORDER BY ds.deck_id, ds.created_at DESC
            ),
            arch_counts AS (
                SELECT archetype_label, COUNT(*) AS deck_count
                FROM other_subs
                GROUP BY archetype_label
                HAVING COUNT(*) >= 2
            ),
            side_cards AS (
                SELECT os.archetype_label, dc.card_id,
                       COUNT(DISTINCT os.deck_id) AS cnt
                FROM other_subs os
                JOIN arch_counts ac ON ac.archetype_label = os.archetype_label
                JOIN deck_cards dc ON dc.deck_submission_id = os.sub_id
                  AND dc.section = 'side'
                GROUP BY os.archetype_label, dc.card_id
            ),
            side_pct AS (
                SELECT sc.archetype_label, sc.card_id, sc.cnt,
                       ROUND(sc.cnt::numeric / ac.deck_count, 4) AS side_pct
                FROM side_cards sc
                JOIN arch_counts ac ON ac.archetype_label = sc.archetype_label
            ),
            ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY archetype_label ORDER BY side_pct DESC
                       ) AS rn
                FROM side_pct
            )
            SELECT r.archetype_label, r.card_id, c.name, c.frame_type,
                   COALESCE(ci.image_url, '') AS image_url,
                   r.side_pct, ac.deck_count
            FROM ranked r
            JOIN cards c ON c.id = r.card_id
            LEFT JOIN card_images ci ON ci.card_id = r.card_id
            JOIN arch_counts ac ON ac.archetype_label = r.archetype_label
            WHERE r.rn <= 15
            ORDER BY r.archetype_label, r.side_pct DESC
            """
        ),
        {"did": deck_id},
    )

    # Group by archetype
    arch_map: dict[str, dict] = {}
    for r in arch_rows.mappings().all():
        lbl = r["archetype_label"]
        if lbl not in arch_map:
            arch_map[lbl] = {"deck_count": int(r["deck_count"]), "cards": []}
        arch_map[lbl]["cards"].append(
            ArchetypeSideCard(
                card_id=r["card_id"],
                name=r["name"],
                frame_type=r["frame_type"],
                image_url=r["image_url"] or _IMG_BASE.format(card_id=r["card_id"]),
                side_pct=float(r["side_pct"]),
            )
        )

    archetypes: list[ArchetypeSideData] = [
        ArchetypeSideData(
            archetype_label=lbl,
            deck_count=v["deck_count"],
            top_side_cards=v["cards"],
        )
        for lbl, v in sorted(arch_map.items(), key=lambda kv: -kv[1]["deck_count"])
    ]

    return SideOptimizerOut(
        deck_id=deck_id,
        deck_title=deck_title,
        side_count=side_count,
        current_side=current_side,
        suggestions=suggestions,
        total_other_decks=total_other_decks,
        has_side_data=has_side_data,
        archetypes=archetypes,
    )
