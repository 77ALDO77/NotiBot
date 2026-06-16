from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.analytics import service

router = APIRouter(tags=["admin-analytics"])


@router.get("/analytics/overview")
async def analytics_overview(db: AsyncSession = Depends(get_db)):
    return await service.get_overview(db)


@router.get("/analytics/lengths")
async def analytics_lengths(db: AsyncSession = Depends(get_db)):
    return await service.get_length_stats(db)


@router.get("/analytics/word-frequency")
async def analytics_word_frequency(
    db: AsyncSession = Depends(get_db),
    scope: str = Query("all", pattern="^(titulos|subtitulos|all)$"),
    top: int = Query(50, ge=5, le=200),
):
    return await service.get_word_frequency(db, scope=scope, top=top)


@router.get("/analytics/word-frequency/by-section")
async def analytics_word_frequency_by_section(
    db: AsyncSession = Depends(get_db),
    top: int = Query(50, ge=5, le=200),
):
    return await service.get_word_frequency_by_section(db, top=top)
