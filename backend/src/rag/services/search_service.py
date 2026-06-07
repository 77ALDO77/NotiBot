from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def search(db: AsyncSession, q: str, limit: int = 5) -> dict:
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


async def get_context(db: AsyncSession, q: str, max_tokens: int = 2000) -> dict:
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
