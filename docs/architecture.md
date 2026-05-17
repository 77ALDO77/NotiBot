# Arquitectura de NotiBot

## Visión general

Tres módulos independientes orquestados con Docker:

```
NotiBot/
├── Scraper/       # Extracción de noticias (Python)
├── backend/       # API REST (FastAPI + PostgreSQL)
├── frontend/      # Interfaz de usuario (Angular 21)
└── docs/          # Documentación y schema SQL
```

## Backend (`backend/`)

FastAPI con SQLAlchemy async + asyncpg. Esqueleto temprano — endpoints mínimos.

```
backend/src/
├── main.py              # FastAPI app, lifespan, CORS
├── api/
│   └── router.py        # GET /api/health, GET /api/news
├── core/
│   ├── config.py         # Settings via pydantic-settings (.env)
│   └── database.py       # Engine async + session factory
└── models/
    └── base.py           # SQLAlchemy DeclarativeBase
```

- **CORS**: configurado desde `CORS_ORIGINS` en `.env`
- **Lifespan**: `engine.dispose()` al apagar
- **Migraciones**: Alembic (`alembic/`), `env.py` lee `DATABASE_URL` de `settings`
- **Endpoints actuales**: `GET /api/health`, `GET /api/news` (retorna `[]`)

## Frontend (`frontend/`)

Angular 21 standalone components, lazy loading, SCSS con design tokens.

```
frontend/src/app/
├── app.ts / app.html / app.scss    # Shell principal
├── app.routes.ts                    # 4 rutas lazy-loaded
├── app.config.ts                    # withComponentInputBinding()
├── app.spec.ts                      # Test vitest
└── features/
    ├── news-feed/                   # Portada (ruta /)
    ├── article-detail/              # Detalle noticia (/article/:id)
    ├── ai-chat/                     # Chat IA (/chat)
    └── auth/                        # Login (/login)
```

- **SCSS**: tokens en `src/styles/_tokens.scss` (Urban Pulse System). Usar `@use`, nunca `@import`
- **Tests**: vitest (`@angular/build:unit-test`, tipos `vitest/globals`)
- **Router**: `withComponentInputBinding()` — `article/:id` pasa `id` como `@Input()` al componente
- **Prettier**: config en `.prettierrc`

### Design tokens

| Token | Valor | Uso |
|-------|-------|-----|
| `$color-brand` | `#1E1B4B` | Deep Indigo (brand/primary) |
| `$color-cta` | `#84CC16` | Acción principal |
| `$color-ai` | `#0EA5E9` | Features IA |
| `$font-headline` | Newsreader | Headlines |
| `$font-body` | Manrope | Body/UI |

## Scraper (`Scraper/`)

Extrae noticias de La República usando sitemaps XML, filtra por ubicación (Lima/Callao) y rango de fechas. Output: `lima_callao_news_YYYYMMDD_HHMMSS.json`.

- `lima_callao_news_scraper.py` — scraper principal (argparse, CLI)
- `larepublica_scraper.py` — variante anterior más simple
- `main.py` — stub (no usar)

El modelo de datos (`Noticia` dataclass) refleja la tabla `noticias` del schema.

## Base de datos

PostgreSQL 16 (`docker compose up postgres`). Schema completo en `docs/database/schema.sql` (23 tablas: `fuentes`, `noticias`, `noticias_contenido`, `noticias_analisis`, `entidades`, `usuarios`, `sesiones_chat`, etc.).

El schema se aplica automáticamente al iniciar el contenedor PostgreSQL (montado en `/docker-entrypoint-initdb.d/`). Las migraciones incrementales se gestionan con Alembic desde el backend.

## Docker

```
                    ┌─────────────┐
                    │   nginx:80  │ (prod)
                    │ ng serve:4200│ (dev)
                    └──────┬──────┘
                           │ /api/* proxy
                    ┌──────▼──────┐
                    │ FastAPI:8000 │
                    └──────┬──────┘
                           │ asyncpg
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │    5432     │
                    └─────────────┘
```

- **Prod**: `docker compose up --build` — frontend servido por nginx (SPA fallback + proxy `/api/*` → backend)
- **Dev**: `docker compose -f docker-compose.yml -f docker-compose.override.yml up --build` — Angular dev server en `:4200`, backend con `--reload`, volúmenes montados `:ro` para hot-reload
- **Schema init**: `docs/database/schema.sql` se monta en `/docker-entrypoint-initdb.d/01-schema.sql` del contenedor postgres

## Flujo de datos (actual)

```
La República sitemaps ──► Scraper ──► JSON output
                                        │
                             (pendiente: insertar en DB)
                                        │
                              Backend API ◄── Frontend (Angular)
```

Las fases de IA (clasificación, NER, resúmenes, RAG) están planificadas en `docs/NotiBot.md` pero no implementadas aún.
