from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.noticias import Noticia, NoticiaContenido
from src.models.fuentes import Fuente


async def get_stats(db: AsyncSession) -> dict:
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

    return {"total_noticias": total, "by_scope": by_scope}


def build_news_query(
    scope: Optional[str] = None,
    distrito: Optional[str] = None,
    provincia: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    q: Optional[str] = None,
    categoria_principal: Optional[str] = None,
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
        stmt = stmt.where(Noticia.titulo.ilike(f"%{q}%"))
    if categoria_principal:
        stmt = stmt.where(Noticia.categoria_principal == categoria_principal)

    return stmt


def serialize_news_row(row) -> dict:
    return {
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
    }


async def get_article(article_id: int, db: AsyncSession) -> dict | None:
    stmt = (
        select(Noticia, NoticiaContenido)
        .outerjoin(NoticiaContenido, Noticia.id == NoticiaContenido.id_noticia)
        .where(Noticia.id == article_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()

    if not row:
        return None

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