from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.pipeline import PipelineJob
from src.pipeline.processor import create_and_process_chunking, process_pending_jobs

router = APIRouter(tags=["admin-pipeline"])


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


@router.post("/pipeline/process", status_code=status.HTTP_200_OK)
async def trigger_pipeline_processing():
    processed = await process_pending_jobs(batch_size=50)
    return {"processed": processed}


@router.post("/pipeline/chunking/{noticia_id}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_chunking(noticia_id: int):
    processed = await create_and_process_chunking(noticia_id)
    return {"noticia_id": noticia_id, "jobs_processed": processed}
