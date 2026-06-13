# NotiBot — AGENTS.md

Plataforma de noticias inteligentes para Lima y Callao. Backend + frontend + PostgreSQL, todo via Docker.

## Comandos rápidos

| Qué | Dónde | Comando |
|-----|-------|---------|
| Backend (local) | `backend/` | `uv run uvicorn src.main:app --reload` (puerto 8000, requiere `.env`) |
| Scraper (local) | `backend/` | `uv run python -m src.scraper.main --db --today` |
| Frontend (local) | `frontend/` | `npm start` (puerto 4200, proxy `/api` → `:8000`) |
| Frontend tests | `frontend/` | `npm test` (vitest via `@angular/build:unit-test`) |
| DB migrations | `backend/` | `uv run alembic upgrade head` |
| Instalar deps Python | `backend/` | `uv sync` |

- `.env` en `backend/` es obligatorio para desarrollo local (pydantic-settings lee del CWD). Contiene `DATABASE_URL` y `SECRET_KEY`. El `.env.example` de referencia está en la raíz del repo.
- `opencode.json` y `.env` están en `.gitignore`.
- Package manager frontend: `npm` (NO yarn/pnpm). Forzado en `package.json` (`packageManager: "npm@11.12.1"`) y `angular.json` (`packageManager: "npm"`).
- No hay CI/CD ni GitHub Actions.
- No hay comandos de lint ni typecheck configurados (ni frontend ni backend).

## Arquitectura

| Módulo | Stack |
|--------|-------|
| `backend/` | FastAPI, SQLAlchemy async, asyncpg, Alembic, **uv**, Python 3.14 (Docker usa `python:3.14-slim-bookworm`; local: uv resuelve con la versión disponible) |
| `frontend/` | Angular 21 standalone, SCSS, vitest, npm |
| `Scraper/` (raíz) | **Deprecado**. Ignorar. El scraper real está en `backend/src/scraper/`. |

## Documentos stale

`README.md` y `docs/architecture.md` — ambos tratan `Scraper/` (raíz) como el módulo activo de scraping y describen un backend mínimo con solo 2 endpoints. Ignorarlos. `docs/NotiBot.md` es design spec, no implementación actual.

## Database

- PostgreSQL remoto en `192.168.3.13:5432` (o Docker local: `docker compose up -d postgres`)
- Schema: `docs/database/schema.sql` (se monta en `/docker-entrypoint-initdb.d/`)
- Credenciales: `notibot` / `notibot_dev_2026` / `notibot`
- Schema fix: `double` → `double precision`, índice GIN en tsvector, extensión `pg_trgm`. Usar versión corregida si se recrea la BD.

## Backend

```
backend/src/
├── main.py              # FastAPI app, lifespan, routers
├── core/                # config.py (pydantic-settings), database.py (async engine)
├── api/router.py        # /api/health, /api/news, /api/stats
├── auth/                # JWT login, register (admin-only), require_admin dep
├── admin/router.py      # /api/admin/* (CRUD fuentes/seeds, pipeline, scraping, vectores)
├── rag/router.py        # /api/rag/search, /api/rag/context (full-text search)
├── models/              # 23 tablas ORM (Base, Fuente, Noticia, PipelineJob, etc.)
├── pipeline/            # chunking + tsvector
├── scraper/             # Scraper integrado (comparte venv con backend)
└── vectores/            # embeddings + PCA 3D (sentence-transformers + torch)
```

### Auth

- Seed: `admin@notibot.local` / `admin123` (rol `admin`)
- `POST /api/auth/login` → JWT. `GET /api/auth/me`. `POST /api/auth/register` (admin-only).
- Columna `rol` en `usuarios` (CHECK: admin | lector) — se agregó con ALTER TABLE, no está en schema.sql.

### Scraper (integrado)

- Entrypoint: `python -m src.scraper.main` desde `backend/`
- 8 fuentes activas (SOURCE_ID 1–8). Todas se ejecutan en modo `--daily`/`--today`. El modo `--date` también activa `_run_daily()` (fix: line 734 de main.py).
- Flags: `--today` (día actual + daily), `--daily` (itera día a día), `--date YYYY-MM-DD`, `--start YYYY-MM-DD` / `--end YYYY-MM-DD`, `--db` (escribe a BD), `--workers N`
- Output JSON: `backend/data/lima_callao_news_YYYYMMDD_HHMMSS.json`
- Clasificación geográfica: keyword/regex contra distritos de Lima + Callao (ubigeos hardcodeados en `DISTRICT_UBIGEO`)
- `db_writer.py`: raw SQL async, sin ORM. Inserta en `noticias` + `noticias_contenido` + `scraping_logs` + `fuentes_seeds` + `pipeline_jobs` (chunking auto-trigger). Dedup: solo `ON CONFLICT (url_original)`; `hash_contenido`/`hash_titulo` se calculan pero no se usan para detectar duplicados.
- También expuesto via API: `POST /api/admin/scraping/run` (async, streaming logs)

#### Fuentes

| ID | Slug | Fuente | Método | Archivo |
|:--:|------|--------|--------|---------|
| 1 | `larepublica` | La República | Sitemap XML | `main.py` (clase `LimaCallaoNewsScraper`) |
| 2 | `elcomercio` | El Comercio | Sitemaps por sección | `sources/elcomercio.py` |
| 3 | `peru21` | Peru21 | **HTML sections** (sitemap roto) | `sources/peru21.py` |
| 4 | `correo` | Diario Correo | RSS Arc XP | `sources/correo.py` |
| 5 | `gestion` | Gestión | RSS Arc XP | `sources/gestion.py` |
| 6 | `trome` | Trome | RSS Arc XP | `sources/trome.py` |
| 7 | `ojo` | Ojo | RSS Arc XP | `sources/ojo.py` |
| 8 | `larazon` | La Razón | Sitemap WordPress | `sources/larazon.py` |

#### Patrones de fuente

| Plataforma | Base | Fuentes |
|-----------|------|---------|
| Arc XP RSS | `_arc_rss.py` → `ArcXpRssScraper` | Correo, Gestion, Trome, Ojo |
| HTML sections | `peru21.py` → `Peru21Scraper` | Peru21 (sitemap roto, scrapea `/{seccion}/`) |
| Sitemap XML | propia clase en `main.py` o `sources/` | La República, El Comercio, Larazon |

#### Gotchas del scraper

- **`engine.dispose()` obligatorio**: entre cada `asyncio.run()` en `main.py`, hacer `await engine.dispose()` para limpiar el pool de conexiones. Si no, asyncpg lanza `Future attached to a different loop`.
- **`--date` activa `_run_daily()`**: antes solo `--today` lo hacía; `--date` iba a `_run_batch()` (solo LR). Fix en main.py:734.
- **Peru21**: sitemap inservible (lastmod de 2012). Se scrapean páginas de sección (`/lima/`, `/politica/`, etc.) con fechas confiables del HTML.
- **Larazon**: Yoast SEO devuelve `articleSection` como array `["Actualidad"]`, no string. Se tomó el primer elemento en `extract_article()`.
- **Ojo**: no todas las section feeds RSS responden con items. Usar solo las confirmadas: `actualidad, politica, locomundo, internacional, ciudad, mujer, columnistas`.
- **Arc XP base**: El RSS incluye `<content:encoded>` con HTML completo → no se necesita scrapear cada artículo individualmente. ~6 HTTP requests por fuente por día.
- **`_scrape_rss_source()`**: helper compartido en `main.py` para todas las fuentes Arc XP RSS. Recibe la clase como parámetro.

### Migraciones (Alembic)

- `alembic.ini` tiene URL hardcodeada, pero `alembic/env.py` lee `settings.DATABASE_URL` de pydantic en runtime. Requiere `.env` en `backend/`.
- Baseline: migración vacía stamped (`9f8b399cbdd8`). **NO usar `--autogenerate`**: los nombres FK del schema.sql difieren de los que genera SQLAlchemy; dropea/recrea todas las FKs.

### Pipeline (chunking + full-text search)

- Jobs: `chunking` (divide artículo en ~350 palabras, guarda en `noticias_chunks`) → `vectorizacion` (tsvector en `noticias_busqueda`)
- Trigger: `POST /api/admin/pipeline/process` (procesa jobs pendientes)
- **BUG FIXEADO — ADVERTENCIA**: en `process_chunking_job` (`pipeline/processor.py:61`), NUNCA nombrar una variable local `text` porque sombrea `sqlalchemy.text` y rompe todas las queries posteriores. El código actual usa `full_text` correctamente.
- Búsqueda pública: `GET /api/rag/search?q=`, `GET /api/rag/context?q=&max_tokens=`

### Vectores 3D (PyTorch)

- Modelo: `paraphrase-multilingual-MiniLM-L12-v2` (~120MB), se carga lazy al primer uso.
- Embeddings 384D → PCA 3D con `torch.pca_lowrank()`. Guarda en `noticias_chunks.embedding` (vector(384)) + `x`, `y`, `z`.
- Trigger: `POST /api/admin/vectores/generate`. Data 3D: `GET /api/admin/vectores/3d?scope=`.
- El pipeline principal (scraping, chunking, búsqueda) no depende de PyTorch.

## Frontend

- **Standalone components**, sin NgModules. Lazy loading con `loadComponent` en `app.routes.ts`.
- **Router**: `withComponentInputBinding()` — `:id` de ruta llega como `@Input()` al componente `ArticleDetail` (el alias `Input as RouteInput` es intencional interno).
- 6 rutas: `/`, `/article/:id`, `/chat`, `/login`, `/admin` (protegida por `AdminGuard`), `**` → redirect `/`.
- **SCSS**: `@use`, nunca `@import`. Design tokens en `src/styles/_tokens.scss`.
- Proxy de desarrollo: `proxy.conf.json` → `/api` → `http://localhost:8000`. Dev siempre espera backend en `:8000`.
- Tests: `npm test` → vitest, builder `@angular/build:unit-test`, tipos `vitest/globals` en tsconfig.spec.json. Sin vitest.config.ts — Angular lo maneja.
- Prettier: `.prettierrc` (printWidth 100, singleQuote, parser angular para HTML).
- Typografías: Newsreader (headlines) + Manrope (body/UI) via Google Fonts en `index.html`.
- Package manager forzado: `npm@11.12.1` (ver `packageManager` en `package.json`).

### Design tokens (Urban Pulse System)

| Token | Valor | Uso |
|-------|-------|-----|
| `$color-brand` / `$color-primary-container` | `#1E1B4B` | Deep Indigo |
| `$color-cta` / `$color-accent-lime` | `#84CC16` | Acción principal |
| `$color-ai` / `$color-accent-electric-blue` | `#0EA5E9` | Solo features IA |
| `$font-headline` | `'Newsreader', serif` | Headlines |
| `$font-body` | `'Manrope', sans-serif` | Body/UI |

## Docker

```bash
docker compose up postgres          # solo DB
docker compose up --build           # prod (frontend nginx :80, backend :8000)
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build  # dev hot-reload (frontend :4200)
docker compose down -v              # borra volúmenes (pgdata)
```

- Dev override: backend monta `./backend/src:/app/src:ro`, frontend usa `npx ng serve` en `:4200`.
- Prod: nginx SPA fallback + proxy `/api/*` → backend:8000.

## Agent Skills

Skills instaladas via `npx skills add`. El AI assistant las carga automáticamente al detectar tareas del stack correspondiente. `skills-lock.json` en la raíz fija las versiones.

| Skill | Stack | Fuente |
|-------|-------|--------|
| `fastapi` | Backend FastAPI/Pydantic/SQLAlchemy | jezweb/claude-skills |
| `angular-developer` | Frontend Angular 21 | angular/skills |
| `angular-new-app` | Scaffolding Angular | angular/skills |
| `postgres-best-practices` | PostgreSQL | neondatabase/postgres-skills |

Skills adicionales (61+ del repo jezweb) cubren diseño, UX, git, testing, docs, etc. Ver `.agents/skills/` para el listado completo.
