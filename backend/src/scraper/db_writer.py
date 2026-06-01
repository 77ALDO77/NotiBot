import hashlib
import json
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import engine
from src.core.utils import utcnow


class NewsDBWriter:
    def __init__(self, source_slug: str = "larepublica"):
        self.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self._source_id: Optional[int] = None
        self._source_slug = source_slug

    async def connect(self):
        self.session = self.session_factory()

    async def close(self):
        if hasattr(self, "session"):
            await self.session.close()

    async def ensure_fuente(self) -> int:
        slug = self._source_slug
        result = await self.session.execute(
            text("SELECT id FROM public.fuentes WHERE slug = :slug"), {"slug": slug}
        )
        row = result.fetchone()
        if row:
            self._source_id = row[0]
            return self._source_id

        now = utcnow()
        source_names = {"larepublica": ("La Republica", "https://larepublica.pe"),
                        "elcomercio": ("El Comercio", "https://elcomercio.pe")}
        nombre, url_base = source_names.get(slug, (slug, f"https://{slug}.pe"))
        result = await self.session.execute(
            text("""
                INSERT INTO public.fuentes (nombre, slug, url_base, activa, confiabilidad, created_at, updated_at)
                VALUES (:nombre, :slug, :url_base, :activa, :confiabilidad, :created_at, :updated_at)
                ON CONFLICT (slug) DO UPDATE SET updated_at = EXCLUDED.updated_at
                RETURNING id
            """),
            {
                "nombre": nombre,
                "slug": slug,
                "url_base": url_base,
                "activa": True,
                "confiabilidad": 0.85,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._source_id = result.fetchone()[0]
        return self._source_id

    async def ensure_fuente_seed(self, sitemap_url: str) -> None:
        result = await self.session.execute(
            text("SELECT id FROM public.fuentes_seeds WHERE id_fuente = :id_fuente AND url_seed = :url_seed"),
            {"id_fuente": self._source_id, "url_seed": sitemap_url},
        )
        if result.fetchone():
            return

        await self.session.execute(
            text("""
                INSERT INTO public.fuentes_seeds (id_fuente, tipo_seed, url_seed, scope_geografico, activa, prioridad, created_at)
                VALUES (:id_fuente, :tipo_seed, :url_seed, :scope_geografico, :activa, :prioridad, :created_at)
            """),
            {
                "id_fuente": self._source_id,
                "tipo_seed": "sitemap",
                "url_seed": sitemap_url,
                "scope_geografico": "desconocido",
                "activa": True,
                "prioridad": 100,
                "created_at": utcnow(),
            },
        )

    async def insert_noticia(self, record: dict, contenido_data: dict) -> Optional[int]:
        now = utcnow()
        record["id_fuente"] = self._source_id
        record["slug_fuente"] = self._source_slug
        record["created_at"] = now
        record["updated_at"] = now
        if "hash_titulo" not in record or not record["hash_titulo"]:
            record["hash_titulo"] = hashlib.sha256(
                (record.get("titulo") or "").encode()
            ).hexdigest()[:32]
        if "hash_contenido" not in record or not record["hash_contenido"]:
            record["hash_contenido"] = hashlib.sha256(
                (contenido_data.get("contenido_limpio") or "").encode()
            ).hexdigest()[:32]

        result = await self.session.execute(
            text("""
                INSERT INTO public.noticias (
                    id_fuente, url_original, url_canonica, url_imagen, slug_fuente,
                    titulo, subtitulo, autor, seccion_fuente, categoria_principal,
                    scope_geografico, provincia, distrito, ubigeo,
                    fecha_publicacion, fecha_actualizacion,
                    hash_titulo, hash_contenido, idioma, es_duplicado,
                    created_at, updated_at
                ) VALUES (
                    :id_fuente, :url_original, :url_canonica, :url_imagen, :slug_fuente,
                    :titulo, :subtitulo, :autor, :seccion_fuente, :categoria_principal,
                    :scope_geografico, :provincia, :distrito, :ubigeo,
                    :fecha_publicacion, :fecha_actualizacion,
                    :hash_titulo, :hash_contenido, :idioma, :es_duplicado,
                    :created_at, :updated_at
                )
                ON CONFLICT (url_original) DO UPDATE SET
                    titulo = EXCLUDED.titulo,
                    subtitulo = EXCLUDED.subtitulo,
                    autor = EXCLUDED.autor,
                    url_imagen = EXCLUDED.url_imagen,
                    fecha_actualizacion = EXCLUDED.fecha_actualizacion,
                    hash_contenido = EXCLUDED.hash_contenido,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """),
            {
                "id_fuente": record.get("id_fuente"),
                "url_original": record.get("url_original"),
                "url_canonica": record.get("url_canonica"),
                "url_imagen": record.get("url_imagen"),
                "slug_fuente": record.get("slug_fuente"),
                "titulo": record.get("titulo"),
                "subtitulo": record.get("subtitulo"),
                "autor": record.get("autor"),
                "seccion_fuente": record.get("seccion_fuente"),
                "categoria_principal": record.get("categoria_principal"),
                "scope_geografico": record.get("scope_geografico", "desconocido"),
                "provincia": record.get("provincia"),
                "distrito": record.get("distrito"),
                "ubigeo": record.get("ubigeo"),
                "fecha_publicacion": record.get("fecha_publicacion"),
                "fecha_actualizacion": record.get("fecha_actualizacion"),
                "hash_titulo": record.get("hash_titulo"),
                "hash_contenido": record.get("hash_contenido"),
                "idioma": record.get("idioma", "es"),
                "es_duplicado": record.get("es_duplicado", False),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
            },
        )
        row = result.fetchone()
        if not row:
            return None

        noticia_id = row[0]
        await self._insert_contenido(noticia_id, contenido_data)
        return noticia_id

    async def _insert_contenido(self, noticia_id: int, data: dict):
        now = utcnow()
        content = data.get("contenido_limpio", "")

        await self.session.execute(
            text("""
                INSERT INTO public.noticias_contenido (
                    id_noticia, titulo_extraido, bajada_extraida,
                    contenido_crudo, contenido_limpio, contenido_html,
                    raw_jsonld, raw_metadata, raw_response,
                    longitud_caracteres, longitud_palabras, calidad_extraccion,
                    created_at, updated_at
                ) VALUES (
                    :id_noticia, :titulo_extraido, :bajada_extraida,
                    :contenido_crudo, :contenido_limpio, :contenido_html,
                    :raw_jsonld, :raw_metadata, :raw_response,
                    :longitud_caracteres, :longitud_palabras, :calidad_extraccion,
                    :created_at, :updated_at
                )
                ON CONFLICT (id_noticia) DO UPDATE SET
                    contenido_limpio = EXCLUDED.contenido_limpio,
                    contenido_html = EXCLUDED.contenido_html,
                    raw_jsonld = EXCLUDED.raw_jsonld,
                    raw_metadata = EXCLUDED.raw_metadata,
                    raw_response = EXCLUDED.raw_response,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id_noticia": noticia_id,
                "titulo_extraido": data.get("titulo_extraido"),
                "bajada_extraida": data.get("bajada_extraida"),
                "contenido_crudo": data.get("contenido_crudo"),
                "contenido_limpio": content,
                "contenido_html": data.get("contenido_html"),
                "raw_jsonld": json.dumps(data.get("raw_jsonld")) if data.get("raw_jsonld") else None,
                "raw_metadata": json.dumps(data.get("raw_metadata")) if data.get("raw_metadata") else None,
                "raw_response": json.dumps(data.get("raw_response")) if data.get("raw_response") else None,
                "longitud_caracteres": len(content) if content else None,
                "longitud_palabras": len(content.split()) if content else None,
                "calidad_extraccion": data.get("calidad_extraccion", "sin_validar"),
                "created_at": now,
                "updated_at": now,
            },
        )

    async def log_scraping(self, nivel: str, mensaje: str, id_noticia: Optional[int] = None, meta: Optional[dict] = None):
        await self.session.execute(
            text("""
                INSERT INTO public.scraping_logs (id_fuente, id_noticia, nivel, mensaje, metadata, created_at)
                VALUES (:id_fuente, :id_noticia, :nivel, :mensaje, :metadata, :created_at)
            """),
            {
                "id_fuente": self._source_id,
                "id_noticia": id_noticia,
                "nivel": nivel,
                "mensaje": mensaje,
                "metadata": json.dumps(meta) if meta else None,
                "created_at": utcnow(),
            },
        )

    async def log_day_summary(self, date_str: str, urls_totales: int, filtradas_geo: int,
                               insertadas: int, errores: int, duplicadas: int = 0):
        await self.log_scraping(
            "info",
            f"Dia {date_str}: {insertadas} insertadas, {errores} errores, {filtradas_geo} filtradas de {urls_totales} URLs",
            meta={
                "tipo": "day_summary",
                "fecha": date_str,
                "urls_totales": urls_totales,
                "filtradas_geo": filtradas_geo,
                "insertadas": insertadas,
                "errores": errores,
                "duplicadas": duplicadas,
            },
        )

    async def create_chunking_job(self, noticia_id: int):
        from src.pipeline.processor import create_chunking_jobs
        await create_chunking_jobs(noticia_id, self.session)

    async def commit(self):
        await self.session.commit()
