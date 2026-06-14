# YGO Intel

Plateforme web d'analyse compétitive Yu-Gi-Oh — import, stockage et analyse de decklists avec des outils d'aide à la décision pour les joueurs de tournoi.

## Fonctionnalités

- **Import de decklists** — fichiers `.ydk` ou saisie manuelle
- **Vérification de légalité** — banlist TCG/OCG en temps réel
- **Comparateur de decks** — core/flex/unique, score de divergence Jaccard, ratios côte à côte
- **Calculateur hypergéométrique** — probabilités d'ouvrir chaque carte ou groupe (starters, handtraps…) en main de 5 ou 6
- **Ratio Advisor** — ratios monster/spell/trap comparés aux références compétitives TCG 2025-2026 et aux moyennes de l'archétype en base
- **Analytics par archétype** — distribution types, attributs, niveaux, évolution
- **Recherche globale** — `Ctrl+K` sur toute la bibliothèque de cartes
- **Sync cartes** — synchronisation depuis YGOProDeck API et EdoPro CDB

## Stack technique

| Couche | Tech |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 async · Alembic · PostgreSQL · Redis / RQ |
| Frontend | SvelteKit 2 · Svelte 5 runes · TypeScript |
| Auth | JWT httpOnly cookie (mono-utilisateur) |
| Infra | Docker Compose · Nginx · GitHub Actions CI |

## Lancement local

### Prérequis

- Docker Desktop
- Node 22+
- Python 3.11+

### Démarrage rapide

```bash
# Infra (PostgreSQL + Redis)
docker compose up -d db redis

# Backend
cd backend
cp .env.example .env        # éditer les variables
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Worker RQ (optionnel — pour les syncs asynchrones)
python start_worker.py

# Frontend
cd frontend
cp .env.example .env
npm install
npm run dev
```

L'application est accessible sur `http://localhost:5173`.

### Variables d'environnement

Copier `backend/.env.example` et `frontend/.env.example` puis adapter :

| Variable | Description |
|---|---|
| `DATABASE_URL` | URL PostgreSQL asyncpg |
| `SECRET_KEY` | Clé JWT (générer avec `openssl rand -hex 32`) |
| `AUTH_ENABLED` | `true` / `false` |
| `AUTH_USERNAME` | Login administrateur |
| `AUTH_PASSWORD` | Mot de passe administrateur |

## Tests

```bash
cd backend

# Tests unitaires
pytest tests/ --ignore=tests/integration -v

# Tests d'intégration (nécessite une base PostgreSQL de test)
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ygo_test \
pytest tests/integration/ -v
```

Le CI GitHub Actions tourne automatiquement sur chaque push touchant `backend/`.

## Structure du projet

```
ygo-deckbuild/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoints FastAPI
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Logique métier
│   ├── alembic/versions/    # Migrations
│   └── tests/               # Unit + intégration
├── frontend/
│   └── src/routes/          # Pages SvelteKit
├── nginx/                   # Config reverse proxy
└── docker-compose.yml
```
