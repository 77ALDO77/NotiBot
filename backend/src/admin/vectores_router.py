from typing import Optional

import numpy as np
import torch
from fastapi import APIRouter, Depends, Query
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
