from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.matchup import (
    ArchetypeMatrixRow,
    DeckMatchupOut,
    MatrixCell,
    MatchResultIn,
    MatchResultRow,
    MatchupMatrixOut,
    MatchupSummary,
)

router = APIRouter(tags=["matchup"])


def _win_rate(wins: int, losses: int, draws: int) -> float:
    total = wins + losses + draws
    if total == 0:
        return 0.0
    return round((wins + 0.5 * draws) / total, 4)


# ── Deck-level endpoints ─────────────────────────────────────────────────────

@router.post("/{deck_id}/match-results", status_code=201)
async def add_match_result(
    deck_id: int,
    body: MatchResultIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict:
    exists = await db.execute(
        text("SELECT 1 FROM decks WHERE id = :did"), {"did": deck_id}
    )
    if not exists.first():
        raise HTTPException(404, "Deck not found")

    result = await db.execute(
        text(
            "INSERT INTO match_results (deck_id, opponent_arch, result, event_date, notes) "
            "VALUES (:did, :arch, :res, :edate, :notes) RETURNING id"
        ),
        {
            "did": deck_id,
            "arch": body.opponent_arch,
            "res": body.result,
            "edate": body.event_date,
            "notes": body.notes,
        },
    )
    new_id = result.scalar_one()
    await db.commit()
    return {"id": new_id}


@router.delete("/{deck_id}/match-results/{result_id}", status_code=204)
async def delete_match_result(
    deck_id: int,
    result_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> Response:
    res = await db.execute(
        text(
            "DELETE FROM match_results WHERE id = :rid AND deck_id = :did RETURNING id"
        ),
        {"rid": result_id, "did": deck_id},
    )
    if not res.first():
        raise HTTPException(404, "Match result not found")
    await db.commit()
    return Response(status_code=204)


@router.get("/{deck_id}/matchup-stats", response_model=DeckMatchupOut)
async def deck_matchup_stats(
    deck_id: int, db: AsyncSession = Depends(get_db)
) -> DeckMatchupOut:
    deck_row = await db.execute(
        text("SELECT title, archetype_label FROM decks WHERE id = :did"),
        {"did": deck_id},
    )
    deck = deck_row.mappings().first()
    if not deck:
        raise HTTPException(404, "Deck not found")

    # Per-matchup aggregates
    agg_rows = await db.execute(
        text(
            """
            SELECT opponent_arch,
                   COUNT(*) FILTER (WHERE result = 'W') AS wins,
                   COUNT(*) FILTER (WHERE result = 'L') AS losses,
                   COUNT(*) FILTER (WHERE result = 'D') AS draws,
                   COUNT(*) AS total
            FROM match_results
            WHERE deck_id = :did
            GROUP BY opponent_arch
            ORDER BY total DESC
            """
        ),
        {"did": deck_id},
    )
    matchup_stats: list[MatchupSummary] = [
        MatchupSummary(
            opponent_arch=r["opponent_arch"],
            wins=int(r["wins"]),
            losses=int(r["losses"]),
            draws=int(r["draws"]),
            total=int(r["total"]),
            win_rate=_win_rate(int(r["wins"]), int(r["losses"]), int(r["draws"])),
        )
        for r in agg_rows.mappings().all()
    ]

    total_matches = sum(m.total for m in matchup_stats)
    overall_wins = sum(m.wins for m in matchup_stats)
    overall_losses = sum(m.losses for m in matchup_stats)
    overall_draws = sum(m.draws for m in matchup_stats)

    # Recent results (last 30)
    recent_rows = await db.execute(
        text(
            """
            SELECT id, opponent_arch, result, event_date, notes, created_at
            FROM match_results
            WHERE deck_id = :did
            ORDER BY created_at DESC
            LIMIT 30
            """
        ),
        {"did": deck_id},
    )
    recent_results: list[MatchResultRow] = [
        MatchResultRow(**dict(r)) for r in recent_rows.mappings().all()
    ]

    return DeckMatchupOut(
        deck_id=deck_id,
        deck_title=deck["title"],
        archetype_label=deck["archetype_label"],
        total_matches=total_matches,
        overall_wins=overall_wins,
        overall_losses=overall_losses,
        overall_draws=overall_draws,
        overall_win_rate=_win_rate(overall_wins, overall_losses, overall_draws),
        matchup_stats=matchup_stats,
        recent_results=recent_results,
    )


# ── Global matrix endpoint (registered on analytics router) ─────────────────

analytics_router = APIRouter(tags=["matchup"])


@analytics_router.get("/matchups", response_model=MatchupMatrixOut)
async def matchup_matrix(db: AsyncSession = Depends(get_db)) -> MatchupMatrixOut:
    rows = await db.execute(
        text(
            """
            SELECT d.archetype_label AS my_arch,
                   mr.opponent_arch,
                   COUNT(*) FILTER (WHERE mr.result = 'W') AS wins,
                   COUNT(*) FILTER (WHERE mr.result = 'L') AS losses,
                   COUNT(*) FILTER (WHERE mr.result = 'D') AS draws,
                   COUNT(*) AS total
            FROM match_results mr
            JOIN decks d ON d.id = mr.deck_id
            WHERE d.archetype_label IS NOT NULL
            GROUP BY d.archetype_label, mr.opponent_arch
            ORDER BY d.archetype_label, total DESC
            """
        )
    )
    data = rows.mappings().all()

    if not data:
        return MatchupMatrixOut(
            archetypes=[], rows=[], total_matches=0, has_data=False
        )

    # Collect all archetypes (both sides of every match)
    arch_total: dict[str, int] = defaultdict(int)
    arch_data: dict[str, dict[str, MatrixCell]] = defaultdict(dict)

    for r in data:
        my = r["my_arch"]
        opp = r["opponent_arch"]
        w, l, d, tot = int(r["wins"]), int(r["losses"]), int(r["draws"]), int(r["total"])
        arch_total[my] += tot
        arch_data[my][opp] = MatrixCell(
            wins=w, losses=l, draws=d, total=tot,
            win_rate=_win_rate(w, l, d),
        )
        # Infer opponent side if opponent_arch is a known archetype
        if opp in arch_data or True:
            arch_total[opp] = arch_total.get(opp, 0)

    # All archetypes that have at least one match as my_arch, sorted by total desc
    archetypes = sorted(arch_data.keys(), key=lambda a: -arch_total[a])
    total_matches = sum(
        cell.total
        for vs in arch_data.values()
        for cell in vs.values()
    )

    matrix_rows: list[ArchetypeMatrixRow] = []
    for arch in archetypes:
        vs = arch_data[arch]
        totals_with_data = [c.win_rate for c in vs.values() if c.win_rate is not None]
        avg_wr = round(sum(totals_with_data) / len(totals_with_data), 4) if totals_with_data else None
        matrix_rows.append(
            ArchetypeMatrixRow(
                archetype=arch,
                total_matches=arch_total[arch],
                avg_win_rate=avg_wr,
                vs=vs,
            )
        )

    return MatchupMatrixOut(
        archetypes=archetypes,
        rows=matrix_rows,
        total_matches=total_matches,
        has_data=True,
    )
