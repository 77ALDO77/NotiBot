# NotiBot

Plataforma de noticias inteligentes para Lima y Callao.

## Estructura

| Módulo | Stack | Descripción |
|--------|-------|-------------|
| `Scraper/` | Python ≥3.14, bs4, requests, uv | Extrae noticias de La República y las guarda en JSON |
| `backend/` | FastAPI, SQLAlchemy async, asyncpg, Alembic, uv | API REST con PostgreSQL |
| `frontend/` | Angular 21 (standalone), npm, SCSS, vitest | Interfaz de usuario |

## Requisitos

- Python ≥3.14 + [uv](https://docs.astral.sh/uv/)
- Node.js + npm
- Docker

## Inicio rápido

```bash
# Instalar dependencias
cd Scraper && uv sync
cd ../backend && uv sync
cd ../frontend && npm install

# Ejecutar scraper
cd Scraper && uv run python lima_callao_news_scraper.py

# Backend (requiere PostgreSQL disponible)
cd backend && uv run alembic upgrade head && uv run uvicorn src.main:app --reload

# Frontend
cd frontend && npm start
```

## Docker

```bash
docker compose up postgres        # solo base de datos
docker compose up --build         # todos los servicios (prod)
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build  # dev (hot-reload)
```

| Servicio | Puerto | Notas |
|----------|--------|-------|
| PostgreSQL | 5432 | 16-alpine, schema auto-aplicado |
| Backend API | 8000 | FastAPI |
| Frontend | 80 / 4200 (dev) | nginx en prod, Angular dev server en dev |

## Documentación

- `AGENTS.md` — guía para agentes de OpenCode
- `docs/NotiBot.md` — especificación de diseño
- `docs/architecture.md` — arquitectura actual
