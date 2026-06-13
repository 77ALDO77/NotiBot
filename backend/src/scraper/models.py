import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class NoticiaRecord:
    url_original: str
    titulo: str
    scope_geografico: str = "desconocido"
    idioma: str = "es"
    es_duplicado: bool = False

    id_fuente: Optional[int] = None
    slug_fuente: Optional[str] = None

    url_canonica: Optional[str] = None
    url_imagen: Optional[str] = None

    subtitulo: Optional[str] = None
    autor: Optional[str] = None
    seccion_fuente: Optional[str] = None
    categoria_principal: Optional[str] = None

    provincia: Optional[str] = None
    distrito: Optional[str] = None
    ubigeo: Optional[str] = None

    fecha_publicacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None

    hash_titulo: Optional[str] = None
    hash_contenido: Optional[str] = None

    id_noticia_canonica: Optional[int] = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.titulo and self.hash_titulo is None:
            self.hash_titulo = hashlib.sha256(self.titulo.encode()).hexdigest()[:32]


def noticia_to_dict(record: NoticiaRecord, contenido: str = "") -> dict:
    d = asdict(record)

    if not d.get("hash_contenido") and contenido:
        d["hash_contenido"] = hashlib.sha256(contenido.encode()).hexdigest()[:32]

    for key in ("fecha_publicacion", "fecha_actualizacion", "created_at", "updated_at"):
        val = d.get(key)
        if isinstance(val, datetime):
            d[key] = val.isoformat()
        elif val is None:
            d[key] = None

    return d
