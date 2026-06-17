# YGO Intel

Plateforme web d'analyse compétitive Yu-Gi-Oh — import, stockage et analyse de decklists avec des outils d'aide à la décision pour les joueurs de tournoi.

## Fonctionnalités

### Gestion des decks
- **Import de decklists** — fichiers `.ydk`, URL / lien YDKE, liste texte collée, import en masse (ZIP / multi-fichiers), ou saisie manuelle dans le builder
- **Deck Builder** — recherche avancée (niveau/rang/link, ATK/DEF, race), suggestions de tech cards basées sur l'archétype, autosave en localStorage, mise en page adaptée mobile
- **Vérification de légalité** — banlist TCG/OCG en temps réel, violations détectées carte par carte, test contre n'importe quelle banlist historique
- **Tags & métadonnées** — archétype, source, notes, tags personnalisés
- **Export** — `.ydk` ou copie de liste texte
- **Partage public** — lien + QR code par deck

### Cartes & Banlists
- **Fiche carte détaillée** (`/cards/[id]`) — image, texte complet, statut banlist actuel, historique des restrictions, decks de la base qui la jouent
- **Replacement Finder** — pour une carte bannie, les cartes que les archétypes concernés ont adoptées en remplacement après le ban
- **Prédiction de banlist** (`/banlists` → onglet Predict) — score de risque heuristique (popularité + récidive historique) sur les cartes non restreintes, disclaimer explicite
- **Diff de banlists** — comparaison visuelle entre deux versions, timeline par carte

### Tournois
- **Saisie de résultats** — lier un deck importé à un tournoi, joueur, placement, score
- **Pages tournoi** (`/tournaments`) — classement, répartition par archétype
- **Tournament Prep** (`/decks/[id]/prep`) — méta attendu (top archétypes par part réelle ou estimée), side deck pondéré contre ce champ, légalité banlist TCG/OCG en un coup d'œil

### Competitive Intelligence Suite

| Module | Route | Description |
|---|---|---|
| **Comparateur de decks** | `/compare` | Core / Flex / Unique entre 2-5 decks, score de divergence Jaccard, ratios côte à côte |
| **Comparateur d'archétypes** | `/analytics/compare` | Meta share, cartes communes/exclusives, évolution côte à côte pour 2-4 archétypes |
| **Probabilités** | `/decks/[id]/probability` | Loi hypergéométrique par carte et groupe — P(≥1) en main de 5 ou 6 |
| **Ratio Advisor** | `/decks/[id]/ratio-advice` | Ratios monster/spell/trap vs. références compétitives TCG et moyennes de l'archétype |
| **Simulateur Monte Carlo** | `/decks/[id]/simulate` | 1 000 à 50 000 mains simulées — taux de victoire, main morte, distribution starters, taux de brique par carte |
| **Score compétitif** | `/decks/[id]/score` | Score 0-100 (grade S→D) sur 4 dimensions : Consistance (40%), Puissance (30%), Méta (20%), Résilience (10%) |
| **Side Optimizer** | `/decks/[id]/side-optimizer` | Popularité DB des cartes de side + matrice archétype × top-15 side cards, score pondéré selon config méta interactive |
| **Matchup Matrix** | `/decks/[id]/matchups` | Log W/L/D par archétype adverse, stats par matchup |
| **Matrice globale** | `/analytics/matchups` | Win rates inter-archétypes sur tous les résultats reportés |
| **Évolution temporelle** | `/analytics/archetypes/[label]/evolution` | Présence mensuelle des cartes dans un archétype — tendances rising/stable/falling |
| **Trending Archetypes** | `/analytics` | Archétypes en hausse/en baisse sur les dernières semaines (détection de tendance par slope) |
| **Meta share vs Win share** | `/analytics` | Popularité d'un archétype vs sa performance réelle en top 8, quand des résultats de tournoi existent |
| **OCG → TCG Pipeline** | `/analytics` | Archétypes OCG-exclusifs avec date de sortie TCG prédite (gap moyen historique) |
| **Analytics archétype** | `/analytics/archetypes/[label]` | Distribution types, attributs, niveaux, core/flex/tech spots |

### Infrastructure
- **Sync cartes** — YGOProDeck API + EdoPro CDB (pré-release OCG)
- **Recherche globale** — `Ctrl+K` sur toute la bibliothèque
- **Images on-demand** — téléchargées à la première demande, servies localement ensuite
- **Worker asynchrone** — syncs non-bloquantes via Redis / RQ
- **Cache Redis** — TTL 5 min sur les endpoints d'analyse coûteux, invalidé à chaque import
- **PWA** — installable sur mobile/desktop, manifest + service worker (app shell offline)

## Stack technique

| Couche | Tech |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 async · Alembic · PostgreSQL 16 · Redis / RQ |
| Frontend | SvelteKit 2 · Svelte 5 runes · TypeScript |
| Auth | JWT httpOnly cookie (mono-utilisateur) |
| Infra | Docker Compose · Nginx · GitHub Actions CI |

## Lancement local

### Prérequis

- Docker Desktop
- Node 22+
- Python 3.10+

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
│   ├── alembic/versions/    # Migrations DB
│   └── tests/               # Unit + intégration
├── frontend/
│   └── src/routes/          # Pages SvelteKit
├── nginx/                   # Config reverse proxy
└── docker-compose.yml
```
