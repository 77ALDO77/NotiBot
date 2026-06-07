---
name: fastapi
description: |
  Build Python APIs with FastAPI, Pydantic v2, and SQLAlchemy 2.0. Covers project structure,
  async patterns, JWT authentication, validation, and database integration with uv package manager.

  Use when: creating Python APIs, setting up FastAPI projects, implementing JWT auth, configuring
  SQLAlchemy async, or troubleshooting 422 validation errors, CORS issues, or async blocking.
---

# FastAPI Skill

Production-tested patterns for FastAPI with Pydantic v2, SQLAlchemy 2.0 async, and JWT authentication.

**Latest Versions** (verified December 2025):
- FastAPI: 0.123.2
- Pydantic: 2.11.7
- SQLAlchemy: 2.0.30
- Uvicorn: 0.35.0
- python-jose: 3.3.0

---

## Quick Start

### Project Setup with uv

```bash
uv init my-api
cd my-api
uv add fastapi[standard] sqlalchemy[asyncio] aiosqlite python-jose[cryptography] passlib[bcrypt]
uv run fastapi dev src/main.py
```

### Minimal Working Example

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="My API")

class Item(BaseModel):
    name: str
    price: float

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/items")
async def create_item(item: Item):
    return item
```

---

## Project Structure (Domain-Based)

```
my-api/
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── auth/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── service.py
│   │   └── dependencies.py
│   ├── items/
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   └── service.py
│   └── shared/
│       └── exceptions.py
└── tests/
```

---

## Core Patterns

### Pydantic Schemas (Validation)

- Use `Field()` for validation constraints
- Separate Create/Update/Response schemas
- `from_attributes=True` enables SQLAlchemy model conversion
- Use `str | None` (Python 3.10+) not `Optional[str]`

### SQLAlchemy Models (Database)

- Use `Mapped[T]` and `mapped_column()` (declarative style)
- `Base` from `DeclarativeBase`
- SQLAlchemy async session with `async_sessionmaker`

### Database Setup (Async)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Router Pattern

- `APIRouter(prefix="/resource", tags=["resource"])`
- Use `Depends(get_db)` for database injection
- `response_model=list[Schema]` for proper validation
- Proper HTTP status codes: 201 for create, 204 for delete

---

## JWT Authentication

### Auth Dependencies

- `OAuth2PasswordBearer(tokenUrl="/auth/login")`
- `get_current_user` dependency extracts user from JWT
- `passlib[bcrypt]` for password hashing
- `python-jose` for JWT encode/decode

### Protect Routes

```python
@router.post("/items")
async def create_item(
    item_in: schemas.ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ...
```

---

## Critical Rules

### Always Do
1. Separate Pydantic schemas from SQLAlchemy models
2. Use async for I/O operations (database, HTTP, file access)
3. Validate with Pydantic Field() - constraints, defaults, descriptions
4. Use dependency injection with Depends()
5. Return proper status codes

### Never Do
1. Never use blocking calls in async routes (no `time.sleep()`)
2. Never put business logic in routes - use service layer
3. Never hardcode secrets - use environment variables
4. Never skip validation - always use Pydantic schemas
5. Never use `*` in CORS origins for production

---

## Common Errors & Fixes

### 422 Unprocessable Entity
Request body doesn't match Pydantic schema. Debug at `/docs` endpoint.

### CORS Errors
Configure `CORSMiddleware` with specific origins, not `"*"` in production.

### Async Blocking
Blocking calls in async routes hang all requests. Use `asyncio.sleep()` instead of `time.sleep()`.

### "Field required" for Optional
Use `str | None = None` not `Optional[str]` without default.

---

## Testing

```python
from httpx import AsyncClient, ASGITransport
from src.main import app

async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    response = await client.get("/")
    assert response.status_code == 200
```

---

## Deployment

```bash
# Development
uv run fastapi dev src/main.py

# Production
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Production with workers
uv add gunicorn
uv run gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
