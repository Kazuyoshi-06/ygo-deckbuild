# Claude Code Project Docs — Yu-Gi-Oh Deck Intelligence

Ce dossier contient tous les fichiers Markdown nécessaires pour piloter le projet avec Claude Code de manière structurée, incrémentale et traçable.

## Fichiers

- `PROJECT_BRIEF.md` — vision produit et objectifs
- `PRODUCT_SPEC.md` — fonctionnalités détaillées
- `TECH_STACK.md` — stack technique retenue
- `ARCHITECTURE.md` — architecture globale
- `DATABASE_SCHEMA.md` — schéma de données
- `INGESTION_AND_SYNC.md` — pipeline cartes, images, banlists, decks
- `UI_UX_GUIDELINES.md` — direction design et expérience utilisateur
- `IMPLEMENTATION_PLAN.md` — plan par étapes
- `TASKS.md` — backlog opérationnel
- `CLAUDE.md` — règles de travail de Claude Code
- `PROMPTS.md` — prompts à utiliser pour lancer chaque étape
- `progress.md` — journal d’avancement mis à jour à chaque fin d’étape

## Mode d’utilisation

1. Ouvrir ce dossier comme documentation de référence du projet.
2. Fournir à Claude Code d’abord le contenu de `CLAUDE.md` puis le prompt de départ contenu dans `PROMPTS.md`.
3. Claude Code doit exécuter une seule étape à la fois.
4. À la fin de chaque étape, Claude Code doit :
   - mettre à jour `progress.md`
   - résumer ce qui a été fait
   - lister les fichiers créés/modifiés
   - attendre validation humaine avant de poursuivre
