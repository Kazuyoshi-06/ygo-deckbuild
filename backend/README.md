# YGO Intel — Backend

FastAPI + SQLAlchemy 2 async backend.

## Dev

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL, VERIFY_SSL, etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Swagger: `http://localhost:8000/docs` (DEBUG=true only)

## Tests

```bash
pip install -r requirements-dev.txt
pytest                            # all tests
pytest tests/test_ydk_parser.py  # just the parser
```

## Data sync (first run)

```bash
# Cards from YGOProDeck
curl -X POST http://localhost:8000/api/v1/admin/sync/cards

# Banlist TCG + OCG
curl -X POST http://localhost:8000/api/v1/admin/sync/banlist

# Pre-release cards from EdoPro (optional, pass your local CDB paths)
curl -X POST http://localhost:8000/api/v1/admin/sync/cards/cdb \
  -H "Content-Type: application/json" \
  -d '["C:/GAMES/ProjectIgnis/expansions/cards.cdb", "C:/GAMES/ProjectIgnis/repositories/delta-bagooska/cards.delta.cdb"]'
```

## Key endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/cards` | Search cards (`?q=`, `?type=`, `?attribute=`) |
| GET | `/api/v1/decks` | List decks |
| POST | `/api/v1/decks/import/ydk` | Import a `.ydk` file |
| GET | `/api/v1/decks/{id}/legality?format=TCG` | Check banlist legality |
| POST | `/api/v1/admin/sync/cards` | Trigger card sync |
| POST | `/api/v1/admin/sync/cards/cdb` | Sync from EdoPro CDB |
| POST | `/api/v1/admin/sync/banlist` | Trigger banlist sync |
| GET | `/api/v1/admin/sync/runs` | List sync history |
