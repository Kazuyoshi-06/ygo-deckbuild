from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.side_optimizer import ArchetypeSideCard, ArchetypeSideData

_IMG = "/api/v1/cards/{card_id}/image"

_ARCHETYPE_MATRIX_SQL = text("""
    WITH other_subs AS (
        SELECT DISTINCT ON (ds.deck_id) ds.id AS sub_id,
               ds.deck_id, d.archetype_label
        FROM deck_submissions ds
        JOIN decks d ON d.id = ds.deck_id
        WHERE d.archetype_label IS NOT NULL
          AND ds.deck_id != :exclude_deck_id
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
           r.side_pct, ac.deck_count
    FROM ranked r
    JOIN cards c ON c.id = r.card_id
    JOIN arch_counts ac ON ac.archetype_label = r.archetype_label
    WHERE r.rn <= :top_n
    ORDER BY r.archetype_label, r.side_pct DESC
""")


async def get_archetype_side_matrix(
    db: AsyncSession, exclude_deck_id: int | None = None, top_n: int = 15
) -> list[ArchetypeSideData]:
    """Per-archetype most-played side deck cards (archetypes with >= 2 decks only)."""
    rows = (await db.execute(
        _ARCHETYPE_MATRIX_SQL,
        {"exclude_deck_id": exclude_deck_id if exclude_deck_id is not None else -1, "top_n": top_n},
    )).mappings().all()

    arch_map: dict[str, dict] = {}
    for r in rows:
        lbl = r["archetype_label"]
        if lbl not in arch_map:
            arch_map[lbl] = {"deck_count": int(r["deck_count"]), "cards": []}
        arch_map[lbl]["cards"].append(
            ArchetypeSideCard(
                card_id=r["card_id"],
                name=r["name"],
                frame_type=r["frame_type"],
                image_url=_IMG.format(card_id=r["card_id"]),
                side_pct=float(r["side_pct"]),
            )
        )

    return [
        ArchetypeSideData(archetype_label=lbl, deck_count=v["deck_count"], top_side_cards=v["cards"])
        for lbl, v in sorted(arch_map.items(), key=lambda kv: -kv[1]["deck_count"])
    ]
