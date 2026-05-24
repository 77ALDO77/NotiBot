from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Noticia(Base):
    __tablename__ = "noticias"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_fuente: Mapped[int | None] = mapped_column(ForeignKey("public.fuentes.id"), nullable=True)
    url_original: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url_canonica: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_imagen: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug_fuente: Mapped[str | None] = mapped_column(Text, nullable=True)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    subtitulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    autor: Mapped[str | None] = mapped_column(Text, nullable=True)
    seccion_fuente: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria_principal: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_geografico: Mapped[str] = mapped_column(Text, default="desconocido", server_default="desconocido")
    provincia: Mapped[str | None] = mapped_column(Text, nullable=True)
    distrito: Mapped[str | None] = mapped_column(Text, nullable=True)
    ubigeo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_publicacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hash_titulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    hash_contenido: Mapped[str | None] = mapped_column(Text, nullable=True)
    idioma: Mapped[str] = mapped_column(Text, default="es", server_default="es")
    es_duplicado: Mapped[bool] = mapped_column(Boolean, default=False, server_default=func.false())
    id_noticia_canonica: Mapped[int | None] = mapped_column(
        ForeignKey("public.noticias.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    fuente = relationship("Fuente", back_populates="noticias", lazy="selectin")
    contenido = relationship("NoticiaContenido", back_populates="noticia", uselist=False, lazy="selectin")
    scraping_logs = relationship("ScrapingLog", back_populates="noticia", lazy="selectin")


class NoticiaContenido(Base):
    __tablename__ = "noticias_contenido"
    __table_args__ = {"schema": "public"}

    id_noticia: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.noticias.id"), primary_key=True
    )
    titulo_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)
    bajada_extraida: Mapped[str | None] = mapped_column(Text, nullable=True)
    contenido_crudo: Mapped[str | None] = mapped_column(Text, nullable=True)
    contenido_limpio: Mapped[str | None] = mapped_column(Text, nullable=True)
    contenido_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_jsonld: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    longitud_caracteres: Mapped[int | None] = mapped_column(Integer, nullable=True)
    longitud_palabras: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calidad_extraccion: Mapped[str] = mapped_column(
        Text, default="sin_validar", server_default="sin_validar"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    noticia = relationship("Noticia", back_populates="contenido", lazy="selectin")
