import json
import traceback
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.models.noticias import Noticia, NoticiaContenido
from src.models.others import NoticiaChunk, NoticiaBusqueda
from src.models.pipeline import PipelineJob
from src.pipeline.chunker import split_text_into_chunks


async def create_chunking_jobs(noticia_id: int, db: AsyncSession):
    now = datetime.now(timezone.utc)
    job = PipelineJob(
        job_type="chunking",
        target_type="noticia",
        target_id=noticia_id,
        estado="pendiente",
        created_at=now,
    )
    db.add(job)
    await db.flush()


async def create_tsvector_jobs(noticia_id: int, db: AsyncSession):
    now = datetime.now(timezone.utc)
    job = PipelineJob(
        job_type="vectorizacion",
        target_type="noticia",
        target_id=noticia_id,
        estado="pendiente",
        created_at=now,
    )
    db.add(job)
    await db.flush()


async def process_chunking_job(job: PipelineJob, db: AsyncSession):
    noticia_id = job.target_id
    job.estado = "ejecutando"
    job.started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        result = await db.execute(
            select(NoticiaContenido).where(NoticiaContenido.id_noticia == noticia_id)
        )
        contenido = result.scalar_one_or_none()

        if not contenido or not contenido.contenido_limpio:
            raise ValueError("No hay contenido para chunking")

        result = await db.execute(
            select(Noticia).where(Noticia.id == noticia_id)
        )
        noticia = result.scalar_one()
        full_text = noticia.titulo + "\n\n" + (contenido.contenido_limpio or "")

        chunks = split_text_into_chunks(full_text)

        for i, chunk_data in enumerate(chunks):
            await db.execute(
                text("""
                    INSERT INTO public.noticias_chunks
                        (id_noticia, chunk_index, texto_chunk, tokens_estimados, inicio_char, fin_char, metadata, created_at)
                    VALUES
                        (:id_noticia, :chunk_index, :texto_chunk, :tokens_estimados, :inicio_char, :fin_char, :metadata, :created_at)
                    ON CONFLICT (id_noticia, chunk_index) DO NOTHING
                """),
                {
                    "id_noticia": noticia_id,
                    "chunk_index": i,
                    "texto_chunk": chunk_data["text"],
                    "tokens_estimados": int(chunk_data["word_count"] * 1.3),
                    "inicio_char": chunk_data["char_start"],
                    "fin_char": chunk_data["char_end"],
                    "metadata": json.dumps({"word_count": chunk_data["word_count"]}),
                    "created_at": datetime.now(timezone.utc),
                },
            )

        job.estado = "completado"
        job.finished_at = datetime.now(timezone.utc)
        await db.flush()

        await create_tsvector_jobs(noticia_id, db)

    except Exception as e:
        job.estado = "error"
        job.ultimo_error = traceback.format_exc()[-500:]
        job.intentos += 1
        job.finished_at = datetime.now(timezone.utc)
        await db.flush()


async def process_tsvector_job(job: PipelineJob, db: AsyncSession):
    noticia_id = job.target_id
    job.estado = "ejecutando"
    job.started_at = datetime.now(timezone.utc)
    await db.flush()

    try:
        result = await db.execute(
            select(Noticia).where(Noticia.id == noticia_id)
        )
        noticia = result.scalar_one()

        await db.execute(
            text("""
                INSERT INTO public.noticias_busqueda (id_noticia, documento_tsv)
                VALUES (
                    :id_noticia,
                    setweight(to_tsvector('spanish', coalesce(:titulo, '')), 'A') ||
                    setweight(to_tsvector('spanish', coalesce(:subtitulo, '')), 'B') ||
                    setweight(to_tsvector('spanish', coalesce(:contenido, '')), 'C')
                )
                ON CONFLICT (id_noticia) DO UPDATE SET
                    documento_tsv = EXCLUDED.documento_tsv
            """),
            {
                "id_noticia": noticia_id,
                "titulo": noticia.titulo,
                "subtitulo": noticia.subtitulo or "",
                "contenido": "",
            },
        )

        result = await db.execute(
            select(NoticiaContenido).where(NoticiaContenido.id_noticia == noticia_id)
        )
        contenido = result.scalar_one_or_none()
        if contenido and contenido.contenido_limpio:
            await db.execute(
                text("""
                    UPDATE public.noticias_busqueda
                    SET documento_tsv = documento_tsv ||
                        setweight(to_tsvector('spanish', :contenido), 'C')
                    WHERE id_noticia = :id_noticia
                """),
                {"id_noticia": noticia_id, "contenido": contenido.contenido_limpio},
            )

        job.estado = "completado"
        job.finished_at = datetime.now(timezone.utc)
        await db.flush()

    except Exception as e:
        job.estado = "error"
        job.ultimo_error = traceback.format_exc()[-500:]
        job.intentos += 1
        job.finished_at = datetime.now(timezone.utc)
        await db.flush()


async def process_pending_jobs(batch_size: int = 20):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PipelineJob)
            .where(PipelineJob.estado == "pendiente")
            .order_by(PipelineJob.prioridad, PipelineJob.created_at)
            .limit(batch_size)
        )
        jobs = result.scalars().all()

        for job in jobs:
            try:
                if job.job_type == "chunking":
                    await process_chunking_job(job, db)
                elif job.job_type == "vectorizacion":
                    await process_tsvector_job(job, db)
            except Exception as e:
                job.estado = "error"
                job.ultimo_error = traceback.format_exc()[-500:]
                job.intentos += 1

        await db.commit()
        return len(jobs)


async def create_and_process_chunking(noticia_id: int):
    async with AsyncSessionLocal() as db:
        await create_chunking_jobs(noticia_id, db)
        await db.commit()

    processed = await process_pending_jobs(batch_size=1)
    return processed
