"""Lógica de análisis exploratorio de datos (EDA) para NotiBot."""

import re
from collections import Counter
from typing import Optional

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CUSTOM_STOPWORDS = frozenset({
    "noticias", "noticia", "lima", "callao", "perú", "peru",
    "comercio", "república", "republica", "día", "que", "del",
    "la", "de", "el", "y", "es", "en", "a", "se", "un", "una",
    "más", "por", "con", "los", "las", "para", "su", "al",
    "como", "lo", "le", "ha", "han", "sus", "era", "si",
    "fue", "no", "ya", "todo", "esta", "este", "esta",
    "hace", "tras", "pero", "muy", "dos", "tres",
})


def _ensure_nltk_data():
    try:
        stopwords.words("spanish")
    except LookupError:
        nltk.download("stopwords", quiet=True)
    try:
        word_tokenize("test", language="spanish")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


def _limpiar_texto(texto: Optional[str]) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    texto = re.sub(r"http\S+|www\S+", "", texto)
    texto = re.sub(r"[^a-záéíóúñ\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _tokenizar_y_filtrar(texto: str) -> list[str]:
    limpio = _limpiar_texto(texto)
    if not limpio:
        return []
    stop_es = set(stopwords.words("spanish")) | CUSTOM_STOPWORDS
    tokens = word_tokenize(limpio, language="spanish")
    return [t for t in tokens if len(t) > 2 and t not in stop_es]


def obtener_frecuencia(textos: list[str], top_n: int = 50) -> list[tuple[str, int]]:
    counter: Counter = Counter()
    for t in textos:
        counter.update(_tokenizar_y_filtrar(t))
    return counter.most_common(top_n)


async def get_overview(db: AsyncSession) -> dict:
    result = await db.execute(text("SELECT count(*) FROM public.noticias"))
    total = result.scalar()

    result = await db.execute(
        text("SELECT count(*) FROM public.noticias WHERE es_duplicado = false")
    )
    unique = result.scalar()
    duplicates = total - unique
    dup_pct = round(100 * duplicates / total, 1) if total else 0.0

    result = await db.execute(
        text("""
            SELECT scope_geografico, count(*) FROM public.noticias
            GROUP BY scope_geografico ORDER BY count(*) DESC
        """)
    )
    by_scope = [{"scope": row[0], "count": row[1]} for row in result.all()]

    result = await db.execute(
        text("""
            SELECT seccion_fuente, count(*) FROM public.noticias
            GROUP BY seccion_fuente ORDER BY count(*) DESC
        """)
    )
    by_seccion = [{"seccion": row[0], "count": row[1]} for row in result.all()]

    result = await db.execute(
        text("""
            SELECT provincia, count(*) FROM public.noticias
            WHERE provincia IS NOT NULL
            GROUP BY provincia ORDER BY count(*) DESC
        """)
    )
    by_provincia = [{"provincia": row[0], "count": row[1]} for row in result.all()]

    result = await db.execute(
        text("""
            SELECT categoria_principal, count(*) FROM public.noticias
            WHERE categoria_principal IS NOT NULL
            GROUP BY categoria_principal ORDER BY count(*) DESC
        """)
    )
    by_categoria = [{"categoria": row[0], "count": row[1]} for row in result.all()]

    result = await db.execute(
        text("""
            SELECT distrito, count(*) FROM public.noticias
            WHERE distrito IS NOT NULL
            GROUP BY distrito ORDER BY count(*) DESC LIMIT 15
        """)
    )
    by_distrito = [{"distrito": row[0], "count": row[1]} for row in result.all()]

    return {
        "total_articles": total,
        "total_unique": unique,
        "total_duplicates": duplicates,
        "duplicate_pct": dup_pct,
        "by_scope": by_scope,
        "by_seccion": by_seccion,
        "by_provincia": by_provincia,
        "by_categoria": by_categoria,
        "by_distrito_top15": by_distrito,
    }


async def get_length_stats(db: AsyncSession) -> dict:
    result = await db.execute(
        text("""
            SELECT
                avg(length(titulo)) as mean,
                min(length(titulo)) as min,
                max(length(titulo)) as max,
                stddev(length(titulo)) as std,
                percentile_cont(0.5) within group (order by length(titulo)) as median,
                avg(array_length(regexp_split_to_array(trim(titulo), '\\s+'), 1)) as mean_words,
                count(*) as total
            FROM public.noticias
            WHERE titulo IS NOT NULL AND trim(titulo) <> ''
        """)
    )
    titulo = _format_stat_row(result.first())

    result = await db.execute(
        text("""
            SELECT
                avg(length(subtitulo)) as mean,
                min(length(subtitulo)) as min,
                max(length(subtitulo)) as max,
                stddev(length(subtitulo)) as std,
                percentile_cont(0.5) within group (order by length(subtitulo)) as median,
                avg(array_length(regexp_split_to_array(trim(subtitulo), '\\s+'), 1)) as mean_words,
                count(*) as total
            FROM public.noticias
            WHERE subtitulo IS NOT NULL AND trim(subtitulo) <> ''
        """)
    )
    subtitulo = _format_stat_row(result.first())

    result = await db.execute(
        text("""
            SELECT
                avg(nc.longitud_caracteres) as mean,
                min(nc.longitud_caracteres) as min,
                max(nc.longitud_caracteres) as max,
                stddev(nc.longitud_caracteres) as std,
                percentile_cont(0.5) within group (order by nc.longitud_caracteres) as median,
                avg(nc.longitud_palabras) as mean_words,
                count(*) as total
            FROM public.noticias_contenido nc
            WHERE nc.longitud_caracteres > 0
        """)
    )
    contenido = _format_stat_row(result.first())

    return {"titulo": titulo, "subtitulo": subtitulo, "contenido": contenido}


def _format_stat_row(row) -> dict:
    return {
        "mean": round(row[0], 1) if row[0] is not None else None,
        "min": round(row[1], 1) if row[1] is not None else None,
        "max": round(row[2], 1) if row[2] is not None else None,
        "std": round(row[3], 1) if row[3] is not None else None,
        "median": round(row[4], 1) if row[4] is not None else None,
        "mean_words": round(row[5], 1) if row[5] is not None else None,
        "total_rows": row[6],
    }


async def get_word_frequency(
    db: AsyncSession, scope: str = "all", top: int = 50
) -> dict:
    _ensure_nltk_data()

    if scope == "titulos":
        result = await db.execute(
            text("SELECT titulo FROM public.noticias WHERE titulo IS NOT NULL AND trim(titulo) <> ''")
        )
        textos = [row[0] for row in result.all()]
    elif scope == "subtitulos":
        result = await db.execute(
            text("SELECT subtitulo FROM public.noticias WHERE subtitulo IS NOT NULL AND trim(subtitulo) <> ''")
        )
        textos = [row[0] for row in result.all()]
    else:
        result = await db.execute(
            text("""
                SELECT coalesce(titulo, '') || ' ' || coalesce(subtitulo, '')
                FROM public.noticias
                WHERE titulo IS NOT NULL OR subtitulo IS NOT NULL
            """)
        )
        textos = [row[0] for row in result.all()]

    freq = obtener_frecuencia(textos, top_n=top)
    total_articles = len(textos)
    words = [
        {"word": w, "count": c, "pct": round(100 * c / total_articles, 2)}
        for w, c in freq
    ]
    return {"scope": scope, "top": top, "total_articles": total_articles, "words": words}


async def get_word_frequency_by_section(
    db: AsyncSession, top: int = 50
) -> dict:
    _ensure_nltk_data()

    result = await db.execute(
        text("""
            SELECT seccion_fuente, titulo, subtitulo FROM public.noticias
            WHERE seccion_fuente IS NOT NULL
        """)
    )
    rows = result.all()

    sections: dict[str, list[str]] = {}
    for seccion, titulo, subtitulo in rows:
        seccion = seccion or "Sin sección"
        if seccion not in sections:
            sections[seccion] = []
        combined = (titulo or "") + " " + (subtitulo or "")
        sections[seccion].append(combined.strip())

    section_results = []
    for seccion, textos in sorted(sections.items(), key=lambda x: -len(x[1])):
        freq = obtener_frecuencia(textos, top_n=top)
        words = [
            {"word": w, "count": c, "pct": round(100 * c / len(textos), 2)}
            for w, c in freq
        ]
        section_results.append({
            "seccion": seccion,
            "total_articles": len(textos),
            "words": words,
        })

    return {"scope": "by_section", "top": top, "sections": section_results}


async def get_lengths_data(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT 
                length(n.titulo) as title_len,
                array_length(regexp_split_to_array(trim(n.titulo), '\\s+'), 1) as title_words,
                length(n.subtitulo) as subtitle_len,
                nc.longitud_caracteres as content_len,
                n.seccion_fuente as seccion
            FROM public.noticias n
            LEFT JOIN public.noticias_contenido nc ON n.id = nc.id_noticia
            WHERE n.titulo IS NOT NULL AND trim(n.titulo) <> ''
        """)
    )
    rows = result.all()
    return [
        {
            "title_len": row[0],
            "title_words": row[1] or 0,
            "subtitle_len": row[2],
            "content_len": row[3],
            "seccion": row[4] or "Sin sección"
        }
        for row in rows
    ]

