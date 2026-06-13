from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.utils import paginate
from src.api.services.news_service import build_news_query, serialize_news_row, get_article, get_stats

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "healthy", "database": "disconnected"}


@api_router.get("/news", tags=["news"])
async def list_news(
    db: AsyncSession = Depends(get_db),
    scope: Optional[str] = Query(None, description="lima_metropolitana | callao | desconocido"),
    distrito: Optional[str] = Query(None),
    provincia: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None, alias="fecha_desde"),
    date_to: Optional[date] = Query(None, alias="fecha_hasta"),
    q: Optional[str] = Query(None, description="Search in title and content"),
    categoria_principal: Optional[str] = Query(None, alias="categoria"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    stmt = build_news_query(scope, distrito, provincia, date_from, date_to, q, categoria_principal)
    result = await paginate(db, stmt, limit=limit, offset=offset, serializer=serialize_news_row)
    result["limit"] = limit
    result["offset"] = offset
    return result


@api_router.get("/news/{article_id}", tags=["news"])
async def get_article_endpoint(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await get_article(article_id, db)
    if not article:
        return {"error": "not found"}, 404
    return article


@api_router.get("/stats", tags=["news"])
async def stats_endpoint(db: AsyncSession = Depends(get_db)):
    return await get_stats(db)
