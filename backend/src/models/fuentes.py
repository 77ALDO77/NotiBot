from datetime import datetime
from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Fuente(Base):
    __tablename__ = "fuentes"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url_base: Mapped[str] = mapped_column(Text, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=func.true())
    confiabilidad: Mapped[float] = mapped_column(Double, default=1.0, server_default="1.0")
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    seeds = relationship("FuenteSeed", back_populates="fuente", lazy="selectin")
    noticias = relationship("Noticia", back_populates="fuente", lazy="selectin")


class FuenteSeed(Base):
    __tablename__ = "fuentes_seeds"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_fuente: Mapped[int] = mapped_column(ForeignKey("public.fuentes.id"), nullable=False)
    tipo_seed: Mapped[str] = mapped_column(Text, nullable=False)
    url_seed: Mapped[str] = mapped_column(Text, nullable=False)
    scope_geografico: Mapped[str] = mapped_column(Text, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=func.true())
    prioridad: Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now()
    )

    fuente = relationship("Fuente", back_populates="seeds", lazy="selectin")
