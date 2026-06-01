from datetime import datetime

from pydantic import BaseModel


class FuenteCreate(BaseModel):
    nombre: str
    slug: str
    url_base: str
    confiabilidad: float = 0.85


class FuenteUpdate(BaseModel):
    nombre: str | None = None
    url_base: str | None = None
    activa: bool | None = None
    confiabilidad: float | None = None


class SeedCreate(BaseModel):
    tipo_seed: str
    url_seed: str
    scope_geografico: str = "desconocido"
    prioridad: int = 100


class PipelineJobResponse(BaseModel):
    id: int
    job_type: str
    target_type: str
    target_id: int
    estado: str
    prioridad: int
    intentos: int
    ultimo_error: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class NoticiaListItem(BaseModel):
    id: int
    titulo: str
    scope_geografico: str
    distrito: str | None
    fecha_publicacion: datetime | None
    estado_procesamiento: str | None

    model_config = {"from_attributes": True}
