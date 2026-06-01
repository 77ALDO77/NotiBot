from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

router = APIRouter(tags=["admin-stats"])


@router.get("/stats")
async def admin_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT count(*) FROM public.noticias"))
    total_noticias = result.scalar()

    result = await db.execute(
        text("SELECT scope_geografico, count(*) FROM public.noticias GROUP BY scope_geografico")
    )
    by_scope = {row[0]: row[1] for row in result.all()}

    result = await db.execute(
        text("""
            SELECT fecha_publicacion::date as dia, count(*)
            FROM public.noticias
            WHERE fecha_publicacion IS NOT NULL
            GROUP BY dia ORDER BY dia DESC LIMIT 30
        """)
    )
    by_day = [{"fecha": row[0].isoformat(), "total": row[1]} for row in result.all()]

    result = await db.execute(
        text("""
            SELECT estado, count(*) FROM public.pipeline_jobs GROUP BY estado
        """)
    )
    pipeline_status = {row[0]: row[1] for row in result.all()}

    result = await db.execute(text("SELECT count(*) FROM public.fuentes WHERE activa = true"))
    fuentes_activas = result.scalar()

    result = await db.execute(
        text("""
            SELECT count(*) FROM public.noticias n
            JOIN public.noticias_contenido nc ON nc.id_noticia = n.id
            WHERE nc.calidad_extraccion = 'valida'
        """)
    )
    validadas = result.scalar()

    result = await db.execute(text("SELECT count(*) FROM public.noticias_chunks"))
    chunks_total = result.scalar()

    return {
        "total_noticias": total_noticias,
        "validadas": validadas,
        "chunks": chunks_total,
        "fuentes_activas": fuentes_activas,
        "by_scope": by_scope,
        "by_day": by_day,
        "pipeline": pipeline_status,
    }
