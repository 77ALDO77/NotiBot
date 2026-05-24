from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Double, ForeignKey, Integer, Text, func, Index
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class Entidad(Base):
    __tablename__ = "entidades"
    __table_args__ = (
        Index("entidades_idx_entidades_tipo_nombre", "tipo", "nombre_normalizado"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        Index("usuarios_idx_usuarios_estado", "estado"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre_usuario: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    correo: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    hash_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    rol: Mapped[str] = mapped_column(Text, default="lector", server_default="lector")
    estado: Mapped[str] = mapped_column(Text, default="activo", server_default="activo")
    preferencias: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NoticiaAnalisis(Base):
    __tablename__ = "noticias_analisis"
    __table_args__ = (
        Index("noticias_analisis_idx_noticias_analisis_estado", "estado_procesamiento", "estado_calidad"),
        {"schema": "public"},
    )

    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True
    )
    resumen_ia: Mapped[str | None] = mapped_column(Text, nullable=True)
    resumen_corto_ia: Mapped[str | None] = mapped_column(Text, nullable=True)
    puntaje_sentimiento: Mapped[float | None] = mapped_column(Double, nullable=True)
    etiqueta_sentimiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevancia_local: Mapped[float | None] = mapped_column(Double, nullable=True)
    score_confiabilidad: Mapped[float | None] = mapped_column(Double, nullable=True)
    score_calidad: Mapped[float | None] = mapped_column(Double, nullable=True)
    clasificacion_tematica: Mapped[str | None] = mapped_column(Text, nullable=True)
    clasificacion_modelo: Mapped[str | None] = mapped_column(Text, nullable=True)
    clasificacion_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado_procesamiento: Mapped[str] = mapped_column(
        Text, default="pendiente", server_default="pendiente"
    )
    estado_calidad: Mapped[str] = mapped_column(
        Text, default="sin_validar", server_default="sin_validar"
    )
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    procesado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )


class NoticiaChunk(Base):
    __tablename__ = "noticias_chunks"
    __table_args__ = (
        Index("noticias_chunks_idx_chunks_noticia", "id_noticia", "chunk_index"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    texto_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_estimados: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inicio_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fin_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    x: Mapped[float | None] = mapped_column(Double, nullable=True)
    y: Mapped[float | None] = mapped_column(Double, nullable=True)
    z: Mapped[float | None] = mapped_column(Double, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class NoticiaBusqueda(Base):
    __tablename__ = "noticias_busqueda"
    __table_args__ = (
        Index("noticias_busqueda_idx_noticias_busqueda_tsv", "documento_tsv", postgresql_using="gin"),
        {"schema": "public"},
    )

    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True
    )
    documento_tsv: Mapped[str] = mapped_column(TSVECTOR, nullable=False)


class NoticiaEntidad(Base):
    __tablename__ = "noticias_entidades"
    __table_args__ = (
        Index("noticias_entidades_idx_noticias_entidades_entidad", "id_entidad"),
        {"schema": "public"},
    )

    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True
    )
    id_entidad: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.entidades.id"), primary_key=True
    )
    relevancia: Mapped[float | None] = mapped_column(Double, nullable=True)
    menciones: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origen_extraccion: Mapped[str | None] = mapped_column(Text, nullable=True)


class NoticiaCategoria(Base):
    __tablename__ = "noticias_categorias"
    __table_args__ = (
        Index("noticias_categorias_idx_noticias_categorias_categoria", "id_categoria"),
        {"schema": "public"},
    )

    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True
    )
    id_categoria: Mapped[int] = mapped_column(
        Integer, ForeignKey("public.categorias.id"), primary_key=True
    )
    peso: Mapped[float | None] = mapped_column(Double, nullable=True)
    origen: Mapped[str | None] = mapped_column(Text, nullable=True)


class NoticiaTag(Base):
    __tablename__ = "noticias_tags"
    __table_args__ = {"schema": "public"}

    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True
    )
    id_tag: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tags.id"), primary_key=True
    )


class SesionChat(Base):
    __tablename__ = "sesiones_chat"
    __table_args__ = (
        Index("sesiones_chat_idx_sesiones_usuario_actividad", "id_usuario", "fecha_ultima_actividad"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.usuarios.id"), nullable=False
    )
    titulo_sesion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(Text, default="activa", server_default="activa")
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    fecha_ultima_actividad: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class MensajeChat(Base):
    __tablename__ = "mensajes_chat"
    __table_args__ = (
        Index("mensajes_chat_idx_mensajes_sesion_fecha", "id_sesion", "fecha"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_sesion: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.sesiones_chat.id"), nullable=False
    )
    rol: Mapped[str] = mapped_column(Text, nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_salida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modelo: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class ReferenciaRag(Base):
    __tablename__ = "referencias_rag"
    __table_args__ = {"schema": "public"}

    id_mensaje: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.mensajes_chat.id"), primary_key=True
    )
    id_noticia: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True, nullable=True
    )
    id_chunk: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.noticias_chunks.id"), primary_key=True, nullable=True
    )
    score_relevancia: Mapped[float | None] = mapped_column(Double, nullable=True)


class Interaccion(Base):
    __tablename__ = "interacciones"
    __table_args__ = (
        Index("interacciones_idx_interacciones_noticia_tipo", "id_noticia", "tipo_interaccion"),
        Index("interacciones_idx_interacciones_usuario_fecha", "id_usuario", "fecha"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.usuarios.id"), nullable=False
    )
    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), nullable=False
    )
    tipo_interaccion: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[float | None] = mapped_column(Double, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class BusquedaUsuario(Base):
    __tablename__ = "busquedas_usuario"
    __table_args__ = (
        Index("busquedas_usuario_idx_busquedas_usuario_fecha", "id_usuario", "fecha"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.usuarios.id"), nullable=False
    )
    query_texto: Mapped[str] = mapped_column(Text, nullable=False)
    filtros: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )


class NoticiaGuardada(Base):
    __tablename__ = "noticias_guardadas"
    __table_args__ = {"schema": "public"}

    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.usuarios.id"), primary_key=True
    )
    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True
    )
    fecha_guardado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
