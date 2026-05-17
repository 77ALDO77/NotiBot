# NotiBot — AGENTS.md

Plataforma de noticias inteligentes para Lima y Callao. Tres módulos independientes + Docker.

## Stacks & entrypoints

| Módulo | Stack | Entrypoint real |
|--------|-------|----------------|
| `Scraper/` | Python ≥3.14, bs4, requests, **uv** | `uv run python lima_callao_news_scraper.py` (NO `main.py` — ese es stub) |
| `frontend/` | Angular 21 standalone, npm, SCSS, **vitest** | `npm start` (ng serve) |
| `backend/` | FastAPI, SQLAlchemy async, asyncpg, Alembic, **uv** | `uv run uvicorn src.main:app --reload` |
| `opencode.json` | MCP Stitch (remote, API key, en `.gitignore`) | Project ID `268876530288821538` |

## Cross-cutting

- `uv sync` para instalar dependencias Python (tanto Scraper/ como backend/)
- Sin comentarios en código a menos que sea indispensable
- `opencode.json` y `.env` están en `.gitignore`
- **Documentos stale** (NO reflejan el código actual): `README.md` (menciona Next.js/bun), `docs/architecture.md` (describe `ai/`, `k8s/`, etc. que no existen). Ignorarlos. `docs/NotiBot.md` es un design spec, no implementación actual.

## Scraper

- Entrypoint: `Scraper/lima_callao_news_scraper.py` (argparse, CLI args)
- `Scraper/larepublica_scraper.py` es scraper anterior más simple
- Output JSON: `lima_callao_news_YYYYMMDD_HHMMSS.json`

## Frontend

- **Standalone components**, sin NgModules
- **Lazy loading**: `loadComponent` en `app.routes.ts` (4 rutas: `/`, `/article/:id`, `/chat`, `/login`)
- **Router**: `withComponentInputBinding()` — el param `:id` llega como `@Input()` al componente ArticleDetail
- **Tests**: `npm test` → vitest (builder `@angular/build:unit-test`, tipos `vitest/globals` en tsconfig.spec.json)
- **SCSS**: `@use`, nunca `@import`. Design tokens en `src/styles/_tokens.scss` (import: `@use '../../../styles/tokens' as *;`)
- **Prettier**: config en `.prettierrc` (printWidth 100, singleQuote, parser angular para HTML)
- Typografías: Newsreader (headlines) + Manrope (body/UI) via Google Fonts en `index.html`

### Design tokens clave (Urban Pulse System)

| Token | Valor | Uso |
|-------|-------|-----|
| `$color-brand` / `$color-primary-container` | `#1E1B4B` | Deep Indigo |
| `$color-cta` / `$color-accent-lime` | `#84CC16` | Acción principal |
| `$color-ai` / `$color-accent-electric-blue` | `#0EA5E9` | Solo features IA |
| `$font-headline` | `'Newsreader', serif` | Headlines |
| `$font-body` | `'Manrope', sans-serif` | Body/UI |

## Backend

- **Esqueleto temprano** — solo 2 endpoints: `GET /api/health` y `GET /api/news` (retorna `[]`)
- FastAPI con lifespan (dispose del engine async al cerrar)
- CORS configurado desde pydantic-settings (`CORS_ORIGINS` del `.env`)
- DB: SQLAlchemy async + asyncpg, engine en `src/core/database.py`
- Migraciones: `cd backend && uv run alembic upgrade head`
- **Quirk Alembic**: `alembic.ini` tiene URL hardcodeada, pero `alembic/env.py` lee `settings.DATABASE_URL` de pydantic en runtime. Correr migraciones requiere `.env` configurado.

## Docker

```bash
docker compose up postgres          # solo DB, puerto 5432
docker compose up --build           # todo (prod-like)
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build  # dev hot-reload
docker compose down -v              # ¡cuidado! borra volúmenes (pgdata)
```

| Servicio | Puerto prod | Puerto dev | Notas |
|----------|-------------|------------|-------|
| `postgres` | 5432 | 5432 | Image 16-alpine, schema.sql auto-aplicado |
| `backend` | 8000 | 8000 | uvicorn --reload en override |
| `frontend` | 80 | **4200** | nginx en prod, `npx ng serve` en dev (override) |

- Prod: frontend servido por nginx (SPA fallback + proxy `/api/*` → backend:8000)
- Dev: Angular dev server en `:4200` via docker-compose override
- Backend override monta `./backend/src:/app/src:ro` para hot-reload
