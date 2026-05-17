# OpenCode Agents: Guia para NotiBot

## Estructura actual

| Directorio | Estado | Stack |
|-----------|--------|-------|
| `Scraper/` | Implementado | Python 3.14+ (uv) |
| `frontend/` | Implementado | Angular 21 (standalone, SCSS) |
| `backend/` | Implementado (esqueleto) | FastAPI + SQLAlchemy async + Alembic |
| `opencode.json` | MCP Stitch | Remote, en `.gitignore` |

## MCP Stitch

El proyecto tiene el MCP de Stitch configurado en `opencode.json` (contiene API key, ignorado en git).
Stitch es usado para generar y obtener pantallas de UI para el frontend.

**Stitch project ID**: `268876530288821538` (Lima Social News AI)
**Design system activo**: Urban Pulse System (Light, Newsreader + Manrope, Deep Indigo #1E1B4B)

Tools disponibles via Stitch MCP: `stitch_get_project`, `stitch_get_screen`, `stitch_list_screens`, `stitch_list_design_systems`, `stitch_generate_screen_from_text`, `stitch_edit_screens`, etc.

## Scraper (Python)

- **Entrypoint real**: `cd Scraper && uv run python lima_callao_news_scraper.py` (no `main.py`)
- **Dependencias**: `cd Scraper && uv sync`
- **Python**: `>=3.14`, dependencias: `bs4`, `requests`
- Los `.json` en `Scraper/` son output de ejecuciones anteriores

## Frontend (Angular 21)

### Comandos esenciales
- **Dev server**: `cd frontend && npm start`
- **Build**: `cd frontend && npm run build`
- **Tests**: `cd frontend && npm test`

### Arquitectura
- **Standalone components** (sin NgModules)
- **Lazy loading** via `loadComponent` en `app.routes.ts`
- **SCSS** con design tokens en `src/styles/_tokens.scss` (`@use`)
- **Tipografias**: Newsreader (headlines) + Manrope (body/UI), cargadas via Google Fonts en `index.html`

### Rutas
| Path | Componente | Archivo |
|------|-----------|---------|
| `/` | NewsFeed (portada) | `features/news-feed/` |
| `/article/:id` | ArticleDetail | `features/article-detail/` |
| `/chat` | AiChat (asistente IA) | `features/ai-chat/` |
| `/login` | Login | `features/auth/` |

### Design tokens (Urban Pulse System)
- **Brand/primary**: `$color-brand` = `#1E1B4B` (Deep Indigo)
- **Accent/CTA**: `$color-cta` = `#84CC16` (Lime Green)
- **AI features**: `$color-ai` = `#0EA5E9` (Electric Blue)
- **Fonts**: `$font-headline: 'Newsreader'`, `$font-body: 'Manrope'`
- Las variables SCSS se importan con `@use '../../../styles/tokens' as *;` en cada componente

### Sass: usar `@use`, NO `@import`
`@import` esta deprecado y causa warnings en build. Siempre usar `@use '...' as *`.

### Angular CLI
- Instalado globalmente (`ng`), version `21.2.9`
- Node.js `v25.9.0` (Angular muestra warning pero compila sin errores)

## Backend (FastAPI)

### Comandos esenciales
- **Dev server**: `cd backend && uv run uvicorn src.main:app --reload`
- **Instalar deps**: `cd backend && uv sync`
- **Migraciones**: `cd backend && uv run alembic upgrade head`
- **Nueva migracion**: `cd backend && uv run alembic revision --autogenerate -m "descripcion"`

### Arquitectura
- **FastAPI** con lifespan para manejar conexion a DB
- **SQLAlchemy async** + asyncpg para PostgreSQL
- **Alembic** para migraciones
- **Pydantic Settings** para config via `.env`
- `src/core/config.py` — Settings cargados de `.env`
- `src/core/database.py` — Engine async + session factory
- `src/models/base.py` — SQLAlchemy DeclarativeBase
- `src/api/router.py` — Endpoints API

### Python
- `>=3.14`, package manager: `uv`
- Dependencias: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic, pydantic-settings, alembic

## Docker / Infraestructura

### Comandos esenciales
- **Levantar todo**: `docker compose up --build`
- **Solo DB**: `docker compose up postgres`
- **Desarrollo (hot-reload)**: `docker compose -f docker-compose.yml -f docker-compose.override.yml up --build`
- **Bajar**: `docker compose down -v`

### Servicios
| Servicio | Puerto | Descripcion |
|----------|--------|-------------|
| `postgres` | 5432 | PostgreSQL 16 + schema.sql auto-aplicado |
| `backend` | 8000 | FastAPI API |
| `frontend` | 80 | Angular servido via nginx (SPA + proxy /api/*) |

### Archivos clave
- `docker-compose.yml` — orquestacion principal (produccion)
- `docker-compose.override.yml` — desarrollo (volumes, hot-reload)
- `.env` — variables de entorno (en `.gitignore`)
- `.env.example` — template sin secretos
- `backend/Dockerfile` — multi-stage (uv build + python slim runtime)
- `frontend/Dockerfile` — multi-stage (node build + nginx runtime)
- `frontend/nginx.conf` — SPA fallback + proxy /api/* al backend
- `docs/database/schema.sql` — schema completo PostgreSQL (se monta en init del contenedor)

## Que NO existe aun
- Tests para Scraper y Backend
- CI/CD
- K8s manifests
- Servicios de IA (NER, sentiment, etc.)

## Convenciones
- Sin comentarios en codigo a menos que sea necesario
- `opencode.json` y `.env` estan en `.gitignore`
- Usar `@use` en SCSS, nunca `@import`
- Los entrypoints reales no siempre son `main.py`: verificar cada modulo
