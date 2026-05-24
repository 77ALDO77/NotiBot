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
- `DATABASE_URL=postgresql+asyncpg://notibot:notibot_dev_2026@192.168.3.13:5432/notibot` — requerido en `.env` para backend y scraper
- **Documentos stale** (NO reflejan el código actual): `README.md` (menciona Next.js/bun), `docs/architecture.md` (describe `ai/`, `k8s/`, etc. que no existen). Ignorarlos. `docs/NotiBot.md` es un design spec, no implementación actual.

## Database

- PostgreSQL en servidor remoto `192.168.3.13:5432` (Debian, usuario `aldo`)
- Levantar: `docker compose up -d postgres` en `/home/aldo/AI/NotiBot`
- Credenciales: `notibot` / `notibot_dev_2026` / `notibot`
- Schema en `docs/database/schema.sql` (montado en `/docker-entrypoint-initdb.d/`)
- **Schema fix aplicado**: `double` → `double precision`, índice GIN en `tsvector`, extensión `pg_trgm`. Si se recrea la BD desde cero, usar la versión corregida (ya está en el repo).

## Scraper

- **Integrado dentro del backend**: `backend/src/scraper/` (comparte venv con el backend)
- Entrypoint: `python -m src.scraper.main` desde `backend/`
- `backend/src/scraper/db_writer.py` — escritura asíncrona a PostgreSQL (raw SQL, sin ORM)
- `backend/src/scraper/sources/elcomercio.py` — scraper de El Comercio (JSON-LD + DOM)
- Output JSON: `backend/data/lima_callao_news_YYYYMMDD_HHMMSS.json`
- **DB write**: flag `--db` inserta en `noticias` + `noticias_contenido` + `scraping_logs` + `fuentes_seeds` + `pipeline_jobs` (chunking)
- Dependencias: `bs4`, `requests`, `asyncpg`, `sqlalchemy[asyncio]` (compartidas con el backend)
- Clasificación geográfica: keyword/regex contra distritos de Lima + Callao (ubigeos hardcodeados)
- **Multi-fuente**: La República (sitemap master) + El Comercio (sitemaps por sección)
- El directorio `Scraper/` raíz está deprecado. Ignorar.

## Frontend

- **Standalone components**, sin NgModules
- **Lazy loading**: `loadComponent` en `app.routes.ts` (5 rutas: `/`, `/article/:id`, `/chat`, `/login`, `/admin`)
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

- FastAPI con lifespan (dispose del engine async al cerrar)
- CORS configurado desde pydantic-settings (`CORS_ORIGINS` como string, parsed via `cors_origins_list` property)
- DB: SQLAlchemy async + asyncpg, engine en `src/core/database.py`
- **Modelos ORM**: 23 tablas mapeadas en `src/models/` (fuentes, noticias, pipeline, others)
- **Endpoints**: `/api/health` (verifica BD real), `/api/news` (filtros: scope, distrito, provincia, fecha_desde, fecha_hasta, q; paginación), `/api/news/{id}` (detalle con contenido), `/api/stats` (totales por scope)
- Migraciones: `cd backend && uv run alembic upgrade head`
- **Quirk Alembic**: `alembic.ini` tiene URL hardcodeada, pero `alembic/env.py` lee `settings.DATABASE_URL` de pydantic en runtime. Requiere `.env` en `backend/` (o cwd).
- **Baseline**: migración vacía stamped (`9f8b399cbdd8`). Autogenerate no usable aún: los nombres FK del schema.sql difieren de los que genera SQLAlchemy; correr `--autogenerate` intentará drop/recreate todas las FKs.

## Auth

- `POST /api/auth/login` → JWT token (bcrypt + python-jose)
- `GET /api/auth/me` → perfil del usuario autenticado
- `POST /api/auth/register` → solo admin puede crear usuarios
- `Dependencias`: `require_admin` protege endpoints `/api/admin/*`
- **Seed**: `admin@notibot.local` / `admin123` (rol `admin`)
- Columna `rol` en `usuarios` (CHECK: admin | lector) — se agregó con ALTER TABLE (no está en schema.sql original)

## Pipeline (chunking + full-text search)

- `backend/src/pipeline/processor.py` — crea chunks y tsvector
- `backend/src/pipeline/chunker.py` — split de texto en chunks de ~350 palabras
- Jobs: `chunking` → divide artículo y guarda en `noticias_chunks`, luego crea job `vectorizacion` → llena `noticias_busqueda` con tsvector
- **⚠️ BUG CRÍTICO**: en `process_chunking_job`, NO usar la variable `text` para almacenar el texto del artículo — sombrea `sqlalchemy.text` y rompe todas las queries posteriores. Usar `full_text` o cualquier otro nombre.
- **Trigger**: `POST /api/admin/pipeline/process` procesa jobs pendientes
- **Chunk por artículo**: `POST /api/admin/pipeline/chunking/{id}`
- **Limpiar errores**: `DELETE /api/admin/pipeline/errors`
- Endpoint público: `GET /api/rag/search?q=` — búsqueda full-text con ts_rank
- Endpoint público: `GET /api/rag/context?q=&max_tokens=` — chunks concatenados como contexto para LLM

## Vectores 3D (PyTorch)

- `backend/src/vectores/embedder.py` — sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`, ~120MB) + torch PCA
- Genera embeddings de 384D para cada chunk → reduce a (x,y,z) con `torch.pca_lowrank()`
- Guarda en `noticias_chunks.embedding` (vector(384)) + `x`, `y`, `z` (double precision)
- **Trigger**: `POST /api/admin/vectores/generate` → vectoriza chunks sin embedding
- **3D data**: `GET /api/admin/vectores/3d?scope=` → coordenadas para Plotly.js scatter3D
- El modelo solo se carga al primer uso. El pipeline principal (scraping, chunking, búsqueda) no depende de PyTorch

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

## Agent Skills

El proyecto tiene skills instaladas en `.agents/skills/`. Son instrucciones especializadas que el AI coding assistant carga automáticamente al detectar tareas relevantes del stack.

| Skill | Stack | Fuente | Actualizar |
|-------|-------|--------|------------|
| `fastapi` | Backend (FastAPI/Pydantic/SQLAlchemy) | [jezweb/claude-skills](https://github.com/jezweb/claude-skills) | `npx skills add jezweb/claude-skills` |
| `angular-developer` | Frontend (Angular 21) | [angular/skills](https://github.com/angular/skills) | `npx skills add angular/skills -y` |
| `angular-new-app` | Frontend (scaffolding) | [angular/skills](https://github.com/angular/skills) | `npx skills add angular/skills -y` |
| `postgres-best-practices` | Database (PostgreSQL) | [neondatabase/postgres-skills](https://github.com/neondatabase/postgres-skills) | `npx skills add neondatabase/postgres-skills -y` |

Skills adicionales (61+ del repo jezweb) cubren diseño, UX, git workflow, testing, docs, etc. Ver `.agents/skills/` para el listado completo.

**Instalación manual de skills nuevas:**
```bash
npx skills add <github-user>/<repo> -y
```
