from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class IngestaUrl(Base):
    __tablename__ = "ingesta_urls"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_fuente: Mapped[int] = mapped_column(ForeignKey("public.fuentes.id"), nullable=False)
    url_descubierta: Mapped[str] = mapped_column(Text, nullable=False)
    url_canonica: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_inferido: Mapped[str] = mapped_column(Text, default="desconocido", server_default="desconocido")
    origen_descubrimiento: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(Text, default="pendiente", server_default="pendiente")
    prioridad: Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    intentos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ultimo_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    estado: Mapped[str] = mapped_column(Text, default="pendiente", server_default="pendiente")
    prioridad: Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    intentos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_intentos: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    ultimo_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScrapingLog(Base):
    __tablename__ = "scraping_logs"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_fuente: Mapped[int | None] = mapped_column(ForeignKey("public.fuentes.id"), nullable=True)
    id_noticia: Mapped[int | None] = mapped_column(ForeignKey("public.noticias.id"), nullable=True)
    nivel: Mapped[str] = mapped_column(Text, nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )

    noticia = relationship("Noticia", back_populates="scraping_logs", lazy="selectin")
