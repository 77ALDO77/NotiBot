from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.rag.services.search_service import search, get_context

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/search")
async def search_rag(
    db: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=2),
    limit: int = Query(5, ge=1, le=20),
):
    return await search(db, q, limit)


@router.get("/context")
async def get_rag_context(
    db: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=2),
    max_tokens: int = Query(2000, ge=500, le=8000),
):
    return await get_context(db, q, max_tokens)
