from datetime import date, datetime, timezone
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.config import settings
from src.models.fuentes import Fuente, FuenteSeed
from src.models.noticias import Noticia
from src.models.others import NoticiaAnalisis
from src.models.pipeline import PipelineJob, ScrapingLog
from src.auth.dependencies import require_admin
from src.models.others import NoticiaChunk
from src.pipeline.processor import create_and_process_chunking, process_pending_jobs
from src.vectores.embedder import encode_texts, reduce_to_3d

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class FuenteCreate(BaseModel):
    nombre: str
    slug: str
    url_base: str
    confiabilidad: float = 0.85


class FuenteUpdate(BaseModel):
    nombre: str | None = None
    url_base: str | None = None
    activa: bool | None = None
    confiabilidad: float | None = None


class SeedCreate(BaseModel):
    tipo_seed: str
    url_seed: str
    scope_geografico: str = "desconocido"
    prioridad: int = 100


class PipelineJobResponse(BaseModel):
    id: int
    job_type: str
    target_type: str
    target_id: int
    estado: str
    prioridad: int
    intentos: int
    ultimo_error: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class NoticiaListItem(BaseModel):
    id: int
    titulo: str
    scope_geografico: str
    distrito: str | None
    fecha_publicacion: datetime | None
    estado_procesamiento: str | None

    model_config = {"from_attributes": True}


@router.get("/fuentes")
async def list_fuentes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fuente).order_by(Fuente.nombre))
    fuentes = []
    for f in result.scalars().all():
        seed_result = await db.execute(
            select(func.count()).select_from(FuenteSeed).where(FuenteSeed.id_fuente == f.id)
        )
        seed_count = seed_result.scalar()
        news_result = await db.execute(
            select(func.count()).select_from(Noticia).where(Noticia.id_fuente == f.id)
        )
        news_count = news_result.scalar()
        fuentes.append({
            "id": f.id,
            "nombre": f.nombre,
            "slug": f.slug,
            "url_base": f.url_base,
            "activa": f.activa,
            "confiabilidad": f.confiabilidad,
            "notas": f.notas,
            "seeds_count": seed_count,
            "noticias_count": news_count,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })
    return fuentes


@router.post("/fuentes", status_code=status.HTTP_201_CREATED)
async def create_fuente(data: FuenteCreate, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    fuente = Fuente(
        nombre=data.nombre,
        slug=data.slug,
        url_base=data.url_base,
        confiabilidad=data.confiabilidad,
        created_at=now,
        updated_at=now,
    )
    db.add(fuente)
    await db.commit()
    await db.refresh(fuente)
    return {"id": fuente.id, "nombre": fuente.nombre, "slug": fuente.slug}


@router.put("/fuentes/{fuente_id}")
async def update_fuente(fuente_id: int, data: FuenteUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fuente).where(Fuente.id == fuente_id))
    fuente = result.scalar_one_or_none()
    if not fuente:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(fuente, key, value)
    fuente.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.delete("/fuentes/{fuente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fuente(fuente_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(FuenteSeed).where(FuenteSeed.id_fuente == fuente_id))
    result = await db.execute(delete(Fuente).where(Fuente.id == fuente_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    await db.commit()


@router.get("/fuentes/{fuente_id}/seeds")
async def list_seeds(fuente_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FuenteSeed)
        .where(FuenteSeed.id_fuente == fuente_id)
        .order_by(FuenteSeed.prioridad)
    )
    return [
        {
            "id": s.id,
            "tipo_seed": s.tipo_seed,
            "url_seed": s.url_seed,
            "scope_geografico": s.scope_geografico,
            "activa": s.activa,
            "prioridad": s.prioridad,
        }
        for s in result.scalars().all()
    ]


@router.post("/fuentes/{fuente_id}/seeds", status_code=status.HTTP_201_CREATED)
async def create_seed(fuente_id: int, data: SeedCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fuente).where(Fuente.id == fuente_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    seed = FuenteSeed(
        id_fuente=fuente_id,
        tipo_seed=data.tipo_seed,
        url_seed=data.url_seed,
        scope_geografico=data.scope_geografico,
        prioridad=data.prioridad,
        created_at=datetime.now(timezone.utc),
    )
    db.add(seed)
    await db.commit()
    await db.refresh(seed)
    return {"id": seed.id, "tipo_seed": seed.tipo_seed, "url_seed": seed.url_seed}


@router.delete("/fuentes/{fuente_id}/seeds/{seed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seed(fuente_id: int, seed_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        delete(FuenteSeed).where(FuenteSeed.id == seed_id, FuenteSeed.id_fuente == fuente_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Seed no encontrado")
    await db.commit()


@router.get("/pipeline")
async def list_pipeline_jobs(
    db: AsyncSession = Depends(get_db),
    estado: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    stmt = select(PipelineJob).order_by(PipelineJob.created_at.desc())
    if estado:
        stmt = stmt.where(PipelineJob.estado == estado)
    if job_type:
        stmt = stmt.where(PipelineJob.job_type == job_type)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar()

    result = await db.execute(stmt.limit(limit).offset(offset))
    jobs = [
        {
            "id": j.id,
            "job_type": j.job_type,
            "target_type": j.target_type,
            "target_id": j.target_id,
            "estado": j.estado,
            "prioridad": j.prioridad,
            "intentos": j.intentos,
            "ultimo_error": j.ultimo_error,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        }
        for j in result.scalars().all()
    ]
    return {"items": jobs, "total": total}


@router.post("/pipeline/{job_id}/retry")
async def retry_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PipelineJob).where(PipelineJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if job.estado not in ("error", "cancelado"):
        raise HTTPException(status_code=400, detail="Solo se pueden reintentar jobs en estado error o cancelado")

    job.estado = "pendiente"
    job.intentos = 0
    job.ultimo_error = None
    job.started_at = None
    job.finished_at = None
    await db.commit()
    return {"ok": True}


@router.delete("/pipeline/errors", status_code=status.HTTP_200_OK)
async def clear_pipeline_errors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(PipelineJob).where(PipelineJob.estado == "error"))
    await db.commit()
    return {"deleted": result.rowcount}


@router.get("/pipeline/stats")
async def pipeline_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PipelineJob.estado, func.count()).group_by(PipelineJob.estado)
    )
    by_status = {row[0]: row[1] for row in result.all()}

    result = await db.execute(text("SELECT count(*) FROM public.noticias_chunks"))
    chunks = result.scalar()

    result = await db.execute(text("SELECT count(*) FROM public.noticias_busqueda"))
    tsvector = result.scalar()

    result = await db.execute(text("SELECT count(*) FROM public.noticias"))
    total = result.scalar()

    return {
        "total_noticias": total,
        "chunks_creados": chunks,
        "busqueda_activada": tsvector,
        "by_status": by_status,
    }


@router.get("/scraping-logs")
async def list_scraping_logs(
    db: AsyncSession = Depends(get_db),
    nivel: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    stmt = select(ScrapingLog).order_by(ScrapingLog.created_at.desc())
    if nivel:
        stmt = stmt.where(ScrapingLog.nivel == nivel)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar()

    result = await db.execute(stmt.limit(limit).offset(offset))
    logs = [
        {
            "id": l.id,
            "id_fuente": l.id_fuente,
            "id_noticia": l.id_noticia,
            "nivel": l.nivel,
            "mensaje": l.mensaje,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in result.scalars().all()
    ]
    return {"items": logs, "total": total}


@router.get("/scraping/logs")
async def get_scraping_logs_rich(
    db: AsyncSession = Depends(get_db),
    fecha: Optional[str] = Query(None, description="YYYY-MM-DD"),
    nivel: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    stmt = select(ScrapingLog).order_by(ScrapingLog.created_at.desc())
    if fecha:
        stmt = stmt.where(ScrapingLog.metadata_.op("->>")("fecha") == fecha)
    if nivel:
        stmt = stmt.where(ScrapingLog.nivel == nivel)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_result.scalar()

    result = await db.execute(stmt.limit(limit).offset(offset))
    logs = []
    for l in result.scalars().all():
        meta = l.metadata_ or {}
        logs.append({
            "id": l.id, "id_fuente": l.id_fuente, "id_noticia": l.id_noticia,
            "nivel": l.nivel, "mensaje": l.mensaje,
            "fecha": meta.get("fecha"), "tipo": meta.get("tipo"),
            "insertadas": meta.get("insertadas"),
            "errores": meta.get("errores"),
            "urls_totales": meta.get("urls_totales"),
            "filtradas_geo": meta.get("filtradas_geo"),
            "duplicadas": meta.get("duplicadas"),
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

    return {"items": logs, "total": total, "limit": limit, "offset": offset}


@router.get("/scraping/logs/daily")
async def get_daily_summaries(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(30, le=90),
):
    result = await db.execute(
        select(ScrapingLog)
        .where(ScrapingLog.metadata_.op("->>")("tipo") == "day_summary")
        .order_by(ScrapingLog.created_at.desc())
        .limit(limit)
    )
    summaries = []
    for l in result.scalars().all():
        meta = l.metadata_ or {}
        summaries.append({
            "id": l.id,
            "fecha": meta.get("fecha"),
            "urls_totales": meta.get("urls_totales"),
            "filtradas_geo": meta.get("filtradas_geo"),
            "insertadas": meta.get("insertadas"),
            "errores": meta.get("errores"),
            "duplicadas": meta.get("duplicadas"),
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

    return {"items": summaries, "total": len(summaries)}


@router.get("/scraping/logs/live")
async def get_live_logs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(30, le=100),
):
    result = await db.execute(
        select(ScrapingLog)
        .order_by(ScrapingLog.created_at.desc())
        .limit(limit)
    )
    logs = []
    for l in result.scalars().all():
        meta = l.metadata_ or {}
        logs.append({
            "id": l.id,
            "nivel": l.nivel,
            "mensaje": l.mensaje,
            "fecha": meta.get("fecha"),
            "tipo": meta.get("tipo"),
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

    return {"items": list(reversed(logs)), "total": len(logs)}


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


@router.post("/pipeline/process", status_code=status.HTTP_200_OK)
async def trigger_pipeline_processing():
    processed = await process_pending_jobs(batch_size=50)
    return {"processed": processed}


@router.post("/pipeline/chunking/{noticia_id}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_chunking(noticia_id: int):
    processed = await create_and_process_chunking(noticia_id)
    return {"noticia_id": noticia_id, "jobs_processed": processed}


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


@router.post("/vectores/generate")
async def generate_embeddings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NoticiaChunk.id, NoticiaChunk.texto_chunk)
        .where(NoticiaChunk.embedding.is_(None))
        .limit(500)
    )
    new_rows = result.all()

    if not new_rows:
        return {"status": "done", "generated": 0, "message": "Todos los chunks ya tienen embedding"}

    new_ids = [r.id for r in new_rows]
    new_texts = [(r.texto_chunk or "")[:2000] for r in new_rows]
    new_embeddings = encode_texts(new_texts)

    result = await db.execute(
        select(NoticiaChunk.id, NoticiaChunk.embedding)
        .where(NoticiaChunk.embedding.isnot(None))
    )
    old_rows = result.all()
    all_ids = [r.id for r in old_rows] + new_ids

    import numpy as np
    old_emb_list = [np.array([float(x) for x in r.embedding.strip("[]").split(",")]) for r in old_rows if r.embedding]
    all_embeddings = np.vstack(old_emb_list + [new_embeddings])

    import torch
    t = torch.from_numpy(all_embeddings.astype(np.float32))
    mean = t.mean(dim=0, keepdim=True)
    t_centered = t - mean
    U, S, V = torch.pca_lowrank(t_centered, q=3)
    all_coords = (t_centered @ V).numpy().astype(np.float64)

    for i, chunk_id in enumerate(all_ids):
        emb_arr = all_embeddings[i]
        emb_arr = emb_arr.astype(np.float64) if isinstance(emb_arr, np.ndarray) else np.array(emb_arr, dtype=np.float64)
        emb_str = ",".join(f"{v:.8f}" for v in emb_arr[:384])
        is_new = i >= len(old_rows)
        if is_new:
            await db.execute(
                text("UPDATE noticias_chunks SET embedding = :emb, x = :x, y = :y, z = :z WHERE id = :id"),
                {"id": chunk_id, "emb": f"[{emb_str}]", "x": float(all_coords[i][0]), "y": float(all_coords[i][1]), "z": float(all_coords[i][2])},
            )
        else:
            await db.execute(
                text("UPDATE noticias_chunks SET x = :x, y = :y, z = :z WHERE id = :id"),
                {"id": chunk_id, "x": float(all_coords[i][0]), "y": float(all_coords[i][1]), "z": float(all_coords[i][2])},
            )

    await db.commit()
    return {"status": "ok", "generated": len(new_ids), "recalibrated": len(old_rows)}


@router.get("/vectores/3d")
async def get_vectores_3d(
    db: AsyncSession = Depends(get_db),
    scope: Optional[str] = Query(None),
    distrito: Optional[str] = Query(None),
    seccion: Optional[str] = Query(None),
):
    stmt = (
        select(
            NoticiaChunk.id,
            NoticiaChunk.chunk_index,
            NoticiaChunk.x,
            NoticiaChunk.y,
            NoticiaChunk.z,
            NoticiaChunk.tokens_estimados,
            NoticiaChunk.texto_chunk,
            Noticia.id.label("noticia_id"),
            Noticia.titulo,
            Noticia.scope_geografico,
            Noticia.distrito,
            Noticia.provincia,
            Noticia.seccion_fuente,
            Noticia.categoria_principal,
        )
        .join(Noticia, NoticiaChunk.id_noticia == Noticia.id)
        .where(NoticiaChunk.x.isnot(None))
    )

    if scope:
        stmt = stmt.where(Noticia.scope_geografico == scope)
    if distrito:
        stmt = stmt.where(func.lower(Noticia.distrito) == distrito.lower())
    if seccion:
        stmt = stmt.where(Noticia.seccion_fuente == seccion)

    result = await db.execute(stmt)
    points = []
    for row in result.all():
        points.append({
            "id": row.id,
            "x": float(row.x),
            "y": float(row.y),
            "z": float(row.z),
            "noticia_id": row.noticia_id,
            "titulo": (row.titulo or "")[:100],
            "scope_geografico": row.scope_geografico,
            "distrito": row.distrito,
            "provincia": row.provincia,
            "seccion_fuente": row.seccion_fuente,
            "categoria_principal": row.categoria_principal,
            "chunk_index": row.chunk_index,
            "tokens": row.tokens_estimados,
            "preview": (row.texto_chunk or "")[:150],
        })

    return {"total": len(points), "points": points}


@router.get("/vectores/graph")
async def get_vectores_graph(
    db: AsyncSession = Depends(get_db),
    scope: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    similarity: float = Query(0.85, ge=0.70, le=0.95),
    max_nodes: int = Query(200, le=500),
):
    cat_filter = ""
    scope_filter = ""
    params: dict = {"sim": similarity}
    if categoria:
        cat_filter = "AND n.categoria_principal = :cat"
        params["cat"] = categoria
    if scope:
        scope_filter = "AND n.scope_geografico = :scope"
        params["scope"] = scope

    result = await db.execute(
        text(f"""
            SELECT nc.id, nc.id_noticia, nc.chunk_index, nc.tokens_estimados as tokens,
                   nc.texto_chunk, n.titulo, n.categoria_principal, n.scope_geografico
            FROM noticias_chunks nc
            JOIN noticias n ON nc.id_noticia = n.id
            WHERE nc.embedding IS NOT NULL
              {cat_filter}
              {scope_filter}
            ORDER BY nc.tokens_estimados DESC
            LIMIT :max
        """),
        {**params, "max": max_nodes},
    )

    nodes = []
    seen_ids = set()
    for row in result.all():
        nodes.append({
            "id": row.id,
            "noticia_id": row.id_noticia,
            "chunk_index": row.chunk_index,
            "tokens": row.tokens or 100,
            "titulo": (row.titulo or "")[:80],
            "categoria": row.categoria_principal or "Sin categoría",
            "scope": row.scope_geografico,
            "preview": (row.texto_chunk or "")[:120],
        })
        seen_ids.add(row.id)

    edges = []
    if len(nodes) > 1:
        result = await db.execute(
            text(f"""
                SELECT a.id as source, b.id as target,
                       1 - (a.embedding <=> b.embedding) as sim
                FROM noticias_chunks a
                JOIN noticias_chunks b ON a.id < b.id
                WHERE a.embedding IS NOT NULL AND b.embedding IS NOT NULL
                  AND 1 - (a.embedding <=> b.embedding) > :sim
                ORDER BY sim DESC
                LIMIT 500
            """),
            {"sim": similarity},
        )
        for row in result.all():
            if row.source in seen_ids and row.target in seen_ids:
                edges.append({
                    "source": row.source,
                    "target": row.target,
                    "similarity": round(float(row.sim), 4),
                })

    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}


@router.get("/scraping/status")
async def get_scraping_status():
    state = _running_scrapers.get("default", {})
    running = bool(state.get("pid"))
    return {
        "running": running,
        "current_day": state.get("current_day"),
        "lines_count": state.get("lines", 0),
        "started_at": state.get("started_at", {}).isoformat() if state.get("started_at") else None,
        "command": state.get("command", ""),
    }


_running_scrapers: dict = {}


@router.post("/scraping/run")
async def trigger_scraping(
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD, single day"),
    today: bool = Query(False),
    daily: bool = Query(False),
):
    import asyncio, os, sys

    cmd = [sys.executable, "-m", "src.scraper.main", "--db"]
    current_day = date or start or (datetime.now().strftime("%Y-%m-%d") if today else None)

    if today:
        cmd.append("--today")
    elif date:
        cmd.extend(["--date", date])
    elif start:
        cmd.extend(["--start", start])
        if end:
            cmd.extend(["--end", end])
    if daily:
        cmd.append("--daily")

    _running_scrapers["default"] = {
        "pid": True,
        "current_day": current_day,
        "lines": 0,
        "started_at": datetime.now(timezone.utc),
        "command": " ".join(cmd),
    }

    asyncio.create_task(_run_scraper_async(cmd, current_day))
    return {"status": "started", "command": " ".join(cmd)}


async def _run_scraper_async(cmd: list, current_day: str | None = None):
    import asyncio as aio
    from src.core.database import AsyncSessionLocal

    proc = await aio.create_subprocess_exec(
        *cmd,
        stdout=aio.subprocess.PIPE,
        stderr=aio.subprocess.STDOUT,
        env={
            **__import__("os").environ,
            "DATABASE_URL": settings.DATABASE_URL,
            "PYTHONUNBUFFERED": "1",
        },
    )

    async def _insert_live_log(nivel: str, mensaje: str, day: str | None = None):
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO public.scraping_logs (id_fuente, nivel, mensaje, metadata, created_at)
                        VALUES (NULL, :nivel, :mensaje, CAST(:meta AS jsonb), :created_at)
                    """),
                    {
                        "nivel": nivel,
                        "mensaje": mensaje[:500],
                        "meta": json.dumps({"tipo": "live", "fecha": day}) if day else None,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                await db.commit()
        except Exception as e:
            import sys
            print(f"[SCRAPER_LIVE_LOG_ERROR] {e}", file=sys.stderr, flush=True)

    state = _running_scrapers.get("default", {})

    try:
        if proc.stdout:
            async for line in proc.stdout:
                raw_line = line.decode("utf-8", errors="replace").strip()
                if not raw_line:
                    continue

                nivel = "error" if "✗" in raw_line or "ERROR" in raw_line.lower() else \
                        "warning" if "WARN" in raw_line.lower() or "⚠" in raw_line else "info"

                await _insert_live_log(nivel, raw_line, current_day)

                state["lines"] = state.get("lines", 0) + 1
                _running_scrapers["default"] = state

                if "DIA:" in raw_line and current_day is None:
                    current_day = raw_line.split("DIA:")[-1].strip()
                    state["current_day"] = current_day

        await proc.wait()
    finally:
        _running_scrapers.pop("default", None)
