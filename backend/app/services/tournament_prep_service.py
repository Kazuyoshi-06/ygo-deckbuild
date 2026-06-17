from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.decks import get_deck_legality
from app.models import Deck
from app.schemas.tournament_prep import ExpectedMetaEntry, TournamentPrepOut, WeightedSideCard
from app.services import analytics_service
from app.services.side_optimizer_service import get_archetype_side_matrix


async def _get_expected_meta(db: AsyncSession, top_n: int) -> tuple[list[ExpectedMetaEntry], str]:
    """Top archetypes by meta share — prefers real tournament data (T2.6), falls back to the deck database."""
    win_share = await analytics_service.get_meta_vs_win_share(db)
    if win_share.has_data:
        ranked = sorted(win_share.entries, key=lambda e: -e.meta_share)[:top_n]
        return (
            [ExpectedMetaEntry(label=e.label, meta_share=e.meta_share, deck_count=e.total_count) for e in ranked],
            "tournament",
        )

    overview = await analytics_service.get_overview(db)
    total = overview.total_decks or 1
    return (
        [
            ExpectedMetaEntry(label=a.label, meta_share=round(a.deck_count / total, 4), deck_count=a.deck_count)
            for a in overview.top_archetypes[:top_n]
        ],
        "deck_database",
    )


async def get_tournament_prep(deck_id: int, db: AsyncSession, top_n: int = 3) -> TournamentPrepOut | None:
    """Pre-tournament briefing for a deck: expected meta, weighted side recommendations, banlist legality."""
    deck = await db.get(Deck, deck_id)
    if not deck:
        return None

    expected_meta, meta_source = await _get_expected_meta(db, top_n)

    side_matrix = await get_archetype_side_matrix(db, exclude_deck_id=deck_id, top_n=15)
    side_by_label = {a.archetype_label: a for a in side_matrix}
    has_side_data = len(side_matrix) > 0

    scores: dict[int, dict] = {}
    for meta_entry in expected_meta:
        arch = side_by_label.get(meta_entry.label)
        if not arch:
            continue
        for card in arch.top_side_cards:
            entry = scores.setdefault(card.card_id, {
                "name": card.name,
                "frame_type": card.frame_type,
                "image_url": card.image_url,
                "weighted_score": 0.0,
                "archetype_coverage": {},
            })
            entry["weighted_score"] += meta_entry.meta_share * card.side_pct
            entry["archetype_coverage"][meta_entry.label] = card.side_pct

    side_recommendations = sorted(
        (
            WeightedSideCard(
                card_id=card_id,
                name=info["name"],
                frame_type=info["frame_type"],
                image_url=info["image_url"],
                weighted_score=round(info["weighted_score"], 4),
                archetype_coverage=info["archetype_coverage"],
            )
            for card_id, info in scores.items()
        ),
        key=lambda c: -c.weighted_score,
    )[:15]

    # Direct call into the existing legality route handler — same pattern already used by
    # decks.update_deck(), which calls get_deck(...) directly rather than duplicating the query.
    # NB: banlist_id must be passed explicitly — its parameter default is a FastAPI
    # `Query(...)` sentinel, not `None`, when this handler is called directly like this.
    legality_tcg = await get_deck_legality(deck_id, format="TCG", banlist_id=None, db=db)
    legality_ocg = await get_deck_legality(deck_id, format="OCG", banlist_id=None, db=db)

    return TournamentPrepOut(
        deck_id=deck_id,
        deck_title=deck.title,
        expected_meta=expected_meta,
        meta_source=meta_source,
        side_recommendations=side_recommendations,
        has_side_data=has_side_data,
        legality_tcg=legality_tcg,
        legality_ocg=legality_ocg,
    )
