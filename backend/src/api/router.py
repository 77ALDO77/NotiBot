from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.noticias import Noticia, NoticiaContenido
from src.models.fuentes import Fuente

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
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    stmt = (
        select(
            Noticia.id,
            Noticia.titulo,
            Noticia.subtitulo,
            Noticia.autor,
            Noticia.url_original,
            Noticia.url_imagen,
            Noticia.scope_geografico,
            Noticia.provincia,
            Noticia.distrito,
            Noticia.ubigeo,
            Noticia.fecha_publicacion,
            Noticia.slug_fuente,
            Noticia.seccion_fuente,
            Noticia.categoria_principal,
            Fuente.nombre.label("fuente_nombre"),
        )
        .outerjoin(Fuente, Noticia.id_fuente == Fuente.id)
        .order_by(Noticia.fecha_publicacion.desc().nulls_last())
    )

    if scope:
        stmt = stmt.where(Noticia.scope_geografico == scope)
    if distrito:
        stmt = stmt.where(func.lower(Noticia.distrito) == distrito.lower())
    if provincia:
        stmt = stmt.where(func.lower(Noticia.provincia) == provincia.lower())
    if date_from:
        stmt = stmt.where(Noticia.fecha_publicacion >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        stmt = stmt.where(Noticia.fecha_publicacion <= datetime.combine(date_to, datetime.max.time()))
    if q:
        stmt = stmt.join(Noticia.contenido).where(
            Noticia.titulo.ilike(f"%{q}%")
            | NoticiaContenido.contenido_limpio.ilike(f"%{q}%")
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        items.append({
            "id": row.id,
            "titulo": row.titulo,
            "subtitulo": row.subtitulo,
            "autor": row.autor,
            "url_original": row.url_original,
            "url_imagen": row.url_imagen,
            "scope_geografico": row.scope_geografico,
            "provincia": row.provincia,
            "distrito": row.distrito,
            "ubigeo": row.ubigeo,
            "fecha_publicacion": row.fecha_publicacion.isoformat() if row.fecha_publicacion else None,
            "slug_fuente": row.slug_fuente,
            "fuente_nombre": row.fuente_nombre,
            "seccion_fuente": row.seccion_fuente,
            "categoria_principal": row.categoria_principal,
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@api_router.get("/news/{article_id}", tags=["news"])
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Noticia, NoticiaContenido)
        .outerjoin(NoticiaContenido, Noticia.id == NoticiaContenido.id_noticia)
        .where(Noticia.id == article_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()

    if not row:
        return {"error": "not found"}, 404

    noticia, contenido = row
    return {
        "id": noticia.id,
        "titulo": noticia.titulo,
        "subtitulo": noticia.subtitulo,
        "autor": noticia.autor,
        "url_original": noticia.url_original,
        "url_imagen": noticia.url_imagen,
        "scope_geografico": noticia.scope_geografico,
        "provincia": noticia.provincia,
        "distrito": noticia.distrito,
        "ubigeo": noticia.ubigeo,
        "fecha_publicacion": noticia.fecha_publicacion.isoformat() if noticia.fecha_publicacion else None,
        "fecha_actualizacion": noticia.fecha_actualizacion.isoformat() if noticia.fecha_actualizacion else None,
        "slug_fuente": noticia.slug_fuente,
        "seccion_fuente": noticia.seccion_fuente,
        "categoria_principal": noticia.categoria_principal,
        "contenido_limpio": contenido.contenido_limpio if contenido else None,
        "contenido_html": contenido.contenido_html if contenido else None,
    }


@api_router.get("/stats", tags=["news"])
async def get_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("""
            SELECT scope_geografico, count(*) as total
            FROM public.noticias
            GROUP BY scope_geografico
            ORDER BY total DESC
        """)
    )
    by_scope = {row[0]: row[1] for row in result.all()}

    result = await db.execute(text("SELECT count(*) FROM public.noticias"))
    total = result.scalar()

    return {
        "total_noticias": total,
        "by_scope": by_scope,
    }
