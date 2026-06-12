"""Exporta noticias de PostgreSQL a JSON para los scripts EDA."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://notibot:notibot_dev_2026@localhost:5432/notibot",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

engine = create_engine(DATABASE_URL)
query = text(
    """
    SELECT
        n.id,
        n.titulo,
        n.subtitulo,
        n.autor,
        n.distrito,
        n.provincia,
        n.scope_geografico,
        n.seccion_fuente,
        n.categoria_principal,
        n.es_duplicado,
        nc.contenido_limpio
    FROM noticias n
    LEFT JOIN noticias_contenido nc ON nc.id_noticia = n.id
    ORDER BY n.fecha_publicacion DESC NULLS LAST
    """
)

df = pd.read_sql(query, engine)
articles = []
for row in df.itertuples(index=False):
    preview = (row.contenido_limpio or "")[:500]
    articles.append(
        {
            "id": int(row.id),
            "titulo": row.titulo,
            "subtitulo": row.subtitulo,
            "autor": row.autor,
            "distrito": row.distrito,
            "provincia": row.provincia,
            "scope_geografico": row.scope_geografico,
            "seccion_normalizada": row.seccion_fuente or row.categoria_principal,
            "es_duplicado": bool(row.es_duplicado),
            "_content_preview": preview,
        }
    )

payload = {
    "source": "postgresql:notibot",
    "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    "total_articles": len(articles),
    "date_range": {"start": None, "end": None},
    "articles": articles,
}

out = Path(__file__).resolve().parent / f"lima_callao_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Exportadas {len(articles)} noticias -> {out.name}")
