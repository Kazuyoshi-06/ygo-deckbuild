from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Deck, DeckSubmission, Player, Tournament
from app.schemas.tournament import (
    PlayerOut,
    SubmitResultIn,
    SubmitResultOut,
    TournamentDetailOut,
    TournamentEntryOut,
    TournamentOut,
    TournamentSummaryOut,
)

router = APIRouter(tags=["tournaments"])


@router.post("/submit-result", response_model=SubmitResultOut, status_code=201)
async def submit_result(
    body: SubmitResultIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SubmitResultOut:
    """Link an existing deck to a tournament entry (find-or-create tournament + player)."""
    deck = await db.get(Deck, body.deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Find or create tournament by (name, event_date) pair
    tournament = await db.scalar(
        select(Tournament)
        .where(
            func.lower(Tournament.name) == body.tournament_name.strip().lower(),
            Tournament.event_date == body.tournament_date,
        )
        .limit(1)
    )
    if not tournament:
        tournament = Tournament(
            name=body.tournament_name.strip(),
            event_date=body.tournament_date,
            format=body.tournament_format,
            location=body.tournament_location,
            participants_count=body.tournament_participants,
        )
        db.add(tournament)
        await db.flush()

    # Find or create player by display_name (case-insensitive)
    player = await db.scalar(
        select(Player)
        .where(func.lower(Player.display_name) == body.player_name.strip().lower())
        .limit(1)
    )
    if not player:
        player = Player(
            display_name=body.player_name.strip(),
            country=body.player_country,
        )
        db.add(player)
        await db.flush()

    # Annotate the latest submission of the deck with tournament context
    submission = await db.scalar(
        select(DeckSubmission)
        .where(DeckSubmission.deck_id == body.deck_id)
        .order_by(DeckSubmission.created_at.desc())
        .limit(1)
    )
    if not submission:
        raise HTTPException(status_code=404, detail="No submission found for this deck")

    submission.tournament_id = tournament.id
    submission.player_id = player.id
    submission.placement = body.placement
    submission.format = body.tournament_format
    submission.event_date = body.tournament_date
    submission.participants_count = body.tournament_participants
    submission.wins = body.wins
    submission.losses = body.losses
    submission.draws = body.draws

    await db.commit()

    return SubmitResultOut(
        tournament=TournamentOut(
            id=tournament.id,
            name=tournament.name,
            event_date=tournament.event_date,
            format=tournament.format,
            location=tournament.location,
            participants_count=tournament.participants_count,
        ),
        player=PlayerOut(
            id=player.id,
            display_name=player.display_name,
            country=player.country,
        ),
        deck_id=body.deck_id,
        submission_id=submission.id,
        placement=body.placement,
    )


@router.get("", response_model=list[TournamentSummaryOut])
async def list_tournaments(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None),
    format: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[TournamentSummaryOut]:
    stmt = select(Tournament)
    if q:
        stmt = stmt.where(Tournament.name.ilike(f"%{q}%"))
    if format:
        stmt = stmt.where(Tournament.format.ilike(format))
    stmt = (
        stmt
        .order_by(nullslast(desc(Tournament.event_date)))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = await db.execute(stmt)
    tournaments = list(rows.scalars())

    if not tournaments:
        return []

    ids = [t.id for t in tournaments]
    counts_result = await db.execute(
        select(DeckSubmission.tournament_id, func.count(DeckSubmission.id))
        .where(DeckSubmission.tournament_id.in_(ids))
        .group_by(DeckSubmission.tournament_id)
    )
    count_map: dict[int, int] = dict(counts_result.all())

    return [
        TournamentSummaryOut(
            id=t.id,
            name=t.name,
            event_date=t.event_date,
            format=t.format,
            location=t.location,
            participants_count=t.participants_count,
            entry_count=count_map.get(t.id, 0),
        )
        for t in tournaments
    ]


@router.get("/{tournament_id}", response_model=TournamentDetailOut)
async def get_tournament(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> TournamentDetailOut:
    tournament = await db.get(Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    rows = await db.execute(
        select(DeckSubmission, Deck, Player)
        .join(Deck, DeckSubmission.deck_id == Deck.id)
        .outerjoin(Player, DeckSubmission.player_id == Player.id)
        .where(DeckSubmission.tournament_id == tournament_id)
        .order_by(nullslast(asc(DeckSubmission.placement)))
    )
    entries = [
        TournamentEntryOut(
            submission_id=sub.id,
            deck_id=deck.id,
            deck_title=deck.title,
            archetype_label=deck.archetype_label,
            player_name=player.display_name if player else None,
            player_country=player.country if player else None,
            placement=sub.placement,
            wins=sub.wins,
            losses=sub.losses,
            draws=sub.draws,
        )
        for sub, deck, player in rows.all()
    ]

    return TournamentDetailOut(
        id=tournament.id,
        name=tournament.name,
        organizer=tournament.organizer,
        event_date=tournament.event_date,
        format=tournament.format,
        location=tournament.location,
        participants_count=tournament.participants_count,
        notes=tournament.notes,
        entries=entries,
    )
