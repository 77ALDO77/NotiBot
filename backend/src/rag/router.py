from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/search")
async def search_rag(
    db: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=2, description="Query to search"),
    limit: int = Query(5, ge=1, le=20),
):
    result = await db.execute(
        text("""
            SELECT
                n.id as noticia_id,
                n.titulo,
                n.url_original,
                n.fecha_publicacion,
                nc.chunk_index,
                nc.texto_chunk,
                nc.tokens_estimados,
                ts_rank(nb.documento_tsv, to_tsquery('spanish', :query)) as rank
            FROM public.noticias_busqueda nb
            JOIN public.noticias n ON n.id = nb.id_noticia
            JOIN public.noticias_chunks nc ON nc.id_noticia = n.id
            WHERE nb.documento_tsv @@ plainto_tsquery('spanish', :query)
            ORDER BY rank DESC, nc.chunk_index
        """),
        {"query": q},
    )

    rows = result.all()
    if not rows:
        return {"query": q, "results": [], "total": 0}

    articles = {}
    for row in rows:
        nid = row.noticia_id
        if nid not in articles:
            articles[nid] = {
                "noticia_id": nid,
                "titulo": row.titulo,
                "url_original": row.url_original,
                "fecha_publicacion": row.fecha_publicacion.isoformat() if row.fecha_publicacion else None,
                "relevancia": round(float(row.rank), 4),
                "chunks": [],
            }
        articles[nid]["chunks"].append({
            "index": row.chunk_index,
            "texto": row.texto_chunk[:800],
            "tokens": row.tokens_estimados,
        })

    sorted_articles = sorted(
        articles.values(), key=lambda a: a["relevancia"], reverse=True
    )[:limit]

    return {
        "query": q,
        "total": len(sorted_articles),
        "results": sorted_articles,
    }


@router.get("/context")
async def get_rag_context(
    db: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=2),
    max_tokens: int = Query(2000, ge=500, le=8000),
):
    result = await db.execute(
        text("""
            SELECT
                n.id as noticia_id,
                n.titulo,
                n.fecha_publicacion,
                nc.chunk_index,
                nc.texto_chunk,
                nc.tokens_estimados,
                ts_rank(nb.documento_tsv, to_tsquery('spanish', :query)) as rank
            FROM public.noticias_busqueda nb
            JOIN public.noticias n ON n.id = nb.id_noticia
            JOIN public.noticias_chunks nc ON nc.id_noticia = n.id
            WHERE nb.documento_tsv @@ plainto_tsquery('spanish', :query)
            ORDER BY rank DESC, nc.chunk_index
        """),
        {"query": q},
    )

    rows = result.all()
    if not rows:
        return {"context": "", "sources": []}

    chunks = []
    sources = set()
    total_tokens = 0

    for row in rows:
        if total_tokens >= max_tokens:
            break
        chunks.append(f"[Fuente: {row.titulo}]\n{row.texto_chunk}")
        sources.add(f"{row.titulo} ({row.fecha_publicacion.date() if row.fecha_publicacion else '?'})")
        total_tokens += row.tokens_estimados or 200

    return {
        "context": "\n\n---\n\n".join(chunks),
        "sources": list(sources)[:10],
        "total_tokens": total_tokens,
    }
