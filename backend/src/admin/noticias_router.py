from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.noticias import Noticia
from src.models.others import NoticiaAnalisis, NoticiaChunk

router = APIRouter(tags=["admin-noticias"])


@router.get("/noticias/{noticia_id}/chunks")
async def get_noticia_chunks(noticia_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NoticiaChunk)
        .where(NoticiaChunk.id_noticia == noticia_id)
        .order_by(NoticiaChunk.chunk_index)
    )
    return [
        {
            "id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "texto_preview": (chunk.texto_chunk or "")[:200],
            "texto_completo": chunk.texto_chunk,
            "tokens_estimados": chunk.tokens_estimados,
            "inicio_char": chunk.inicio_char,
            "fin_char": chunk.fin_char,
        }
        for chunk in result.scalars().all()
    ]


@router.get("/noticias")
async def list_noticias_admin(
    db: AsyncSession = Depends(get_db),
    scope: Optional[str] = Query(None),
    estado: Optional[str] = Query(None, alias="estado_procesamiento"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    stmt = (
        select(
            Noticia.id,
            Noticia.titulo,
            Noticia.scope_geografico,
            Noticia.distrito,
            Noticia.fecha_publicacion,
            NoticiaAnalisis.estado_procesamiento,
            Noticia.categoria_principal,
        )
        .outerjoin(NoticiaAnalisis, Noticia.id == NoticiaAnalisis.id_noticia)
        .order_by(Noticia.fecha_publicacion.desc().nulls_last())
    )

    if scope:
        stmt = stmt.where(Noticia.scope_geografico == scope)
    if estado:
        stmt = stmt.where(NoticiaAnalisis.estado_procesamiento == estado)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar()

    result = await db.execute(stmt.limit(limit).offset(offset))
    items = []
    for row in result.all():
        items.append({
            "id": row.id,
            "titulo": row.titulo[:100],
            "scope_geografico": row.scope_geografico,
            "distrito": row.distrito,
            "fecha_publicacion": row.fecha_publicacion.isoformat() if row.fecha_publicacion else None,
            "estado_procesamiento": row.estado_procesamiento or "pendiente",
            "categoria_principal": row.categoria_principal,
        })

    return {"items": items, "total": total}
