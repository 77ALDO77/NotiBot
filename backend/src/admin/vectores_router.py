from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Query
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.noticias import Noticia
from src.models.others import NoticiaChunk
from src.vectores.embedder import encode_texts, reduce_to_3d

router = APIRouter(tags=["admin-vectores"])


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

    old_emb_list = [
        np.array([float(x) for x in r.embedding.strip("[]").split(",")])
        for r in old_rows if r.embedding
    ]
    all_embeddings = np.vstack(old_emb_list + [new_embeddings])

    all_coords = reduce_to_3d(all_embeddings)

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
    categoria: Optional[str] = Query(None, alias="categoria_principal"),
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
    if categoria:
        stmt = stmt.where(Noticia.categoria_principal == categoria)

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


def _compute_tfidf_edges(texts: list[str], ids: list[int], threshold: float,
                         categories: list[str] | None = None) -> list[dict]:
    if len(texts) < 2:
        return []
    vectorizer = TfidfVectorizer(max_features=4000, stop_words=None, lowercase=True,
                                 strip_accents='unicode')
    tfidf = vectorizer.fit_transform(texts)
    sim_matrix = cosine_similarity(tfidf)
    edges = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if categories and categories[i] != categories[j]:
                continue
            s = float(sim_matrix[i][j])
            if s > threshold:
                edges.append({"source": ids[i], "target": ids[j], "similarity": round(s, 4)})
    return edges


@router.get("/vectores/graph")
async def get_vectores_graph(
    db: AsyncSession = Depends(get_db),
    scope: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    similarity: float = Query(0.15, ge=0.05, le=0.60),
    max_nodes: int = Query(200, le=500),
):
    cat_filter = ""
    scope_filter = ""
    params: dict = {}
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
            WHERE nc.texto_chunk IS NOT NULL AND length(nc.texto_chunk) > 50
              {cat_filter}
              {scope_filter}
            ORDER BY nc.tokens_estimados DESC
            LIMIT :max
        """),
        {**params, "max": max_nodes},
    )
    rows = result.all()
    if not rows:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

    nodes = []
    texts = []
    ids_list = []
    categories = []
    for row in rows:
        cat = row.categoria_principal or "Sin categoría"
        nodes.append({
            "id": row.id,
            "noticia_id": row.id_noticia,
            "chunk_index": row.chunk_index,
            "tokens": row.tokens or 100,
            "titulo": (row.titulo or "")[:80],
            "categoria": cat,
            "scope": row.scope_geografico,
            "preview": (row.texto_chunk or "")[:120],
        })
        texts.append(row.texto_chunk or "")
        ids_list.append(row.id)
        categories.append(cat)

    edges = _compute_tfidf_edges(texts, ids_list, similarity, categories)

    # Filter nodes to only connected ones
    connected = set()
    for e in edges:
        connected.add(e["source"])
        connected.add(e["target"])
    if connected:
        nodes = [n for n in nodes if n["id"] in connected]

    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}


@router.get("/vectores/3d/articulos")
async def get_vectores_3d_articulos(
    db: AsyncSession = Depends(get_db),
    scope: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None, alias="categoria_principal"),
):
    cat_filter = "AND n.categoria_principal = :cat" if categoria else ""
    scope_filter = "AND n.scope_geografico = :scope" if scope else ""
    params: dict = {}
    if categoria:
        params["cat"] = categoria
    if scope:
        params["scope"] = scope

    result = await db.execute(
        text(f"""
            SELECT n.id, n.titulo, n.categoria_principal, n.scope_geografico,
                   n.distrito, n.provincia, n.seccion_fuente,
                   AVG(nc.x)::double precision AS cx,
                   AVG(nc.y)::double precision AS cy,
                   AVG(nc.z)::double precision AS cz,
                   SUM(nc.tokens_estimados)::int AS total_tokens,
                   COUNT(nc.id)::int AS chunks,
                   substring(MAX(nc.texto_chunk), 1, 150) AS preview
            FROM noticias_chunks nc
            JOIN noticias n ON nc.id_noticia = n.id
            WHERE nc.x IS NOT NULL
              {cat_filter}
              {scope_filter}
            GROUP BY n.id
            ORDER BY total_tokens DESC
        """),
        params if params else None,
    )

    points = []
    for row in result.all():
        points.append({
            "id": row.id,
            "x": float(row.cx),
            "y": float(row.cy),
            "z": float(row.cz),
            "noticia_id": row.id,
            "titulo": (row.titulo or "")[:100],
            "scope_geografico": row.scope_geografico,
            "distrito": row.distrito,
            "provincia": row.provincia,
            "seccion_fuente": row.seccion_fuente,
            "categoria_principal": row.categoria_principal,
            "chunk_index": 0,
            "tokens": row.total_tokens,
            "preview": row.preview or "",
            "chunks_count": row.chunks,
        })

    return {"total": len(points), "points": points}


@router.get("/vectores/graph/articulos")
async def get_vectores_graph_articulos(
    db: AsyncSession = Depends(get_db),
    scope: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None, alias="categoria_principal"),
    similarity: float = Query(0.12, ge=0.05, le=0.60),
    max_nodes: int = Query(100, le=250),
):
    cat_filter = "AND n.categoria_principal = :cat" if categoria else ""
    scope_filter = "AND n.scope_geografico = :scope" if scope else ""
    params: dict = {}
    if categoria:
        params["cat"] = categoria
    if scope:
        params["scope"] = scope

    result = await db.execute(
        text(f"""
            SELECT n.id, n.titulo, n.categoria_principal, n.scope_geografico,
                   SUM(nc.tokens_estimados)::int AS total_tokens,
                   COUNT(nc.id)::int AS chunks_count,
                   substring(MAX(nc.texto_chunk), 1, 300) AS preview
            FROM noticias_chunks nc
            JOIN noticias n ON nc.id_noticia = n.id
            WHERE nc.texto_chunk IS NOT NULL AND length(nc.texto_chunk) > 50
              {cat_filter}
              {scope_filter}
            GROUP BY n.id
            ORDER BY total_tokens DESC
            LIMIT :max
        """),
        {**params, "max": max_nodes},
    )
    rows = result.all()
    if not rows:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

    nodes = []
    texts = []
    ids_list = []
    categories = []
    for row in rows:
        cat = row.categoria_principal or "Sin categoría"
        preview = row.preview or ""
        # Use titulo + preview for better TF-IDF matching
        full_text = f"{(row.titulo or '')} {preview}"
        nodes.append({
            "id": row.id,
            "noticia_id": row.id,
            "chunk_index": 0,
            "tokens": row.total_tokens or 100,
            "titulo": (row.titulo or "")[:80],
            "categoria": cat,
            "scope": row.scope_geografico,
            "preview": preview[:150],
            "chunks_count": row.chunks_count or 0,
        })
        texts.append(full_text)
        ids_list.append(row.id)
        categories.append(cat)

    edges = _compute_tfidf_edges(texts, ids_list, similarity, categories)

    connected = set()
    for e in edges:
        connected.add(e["source"])
        connected.add(e["target"])
    if connected:
        nodes = [n for n in nodes if n["id"] in connected]

    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}
