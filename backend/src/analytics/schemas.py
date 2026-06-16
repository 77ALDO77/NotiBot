from pydantic import BaseModel


class ScopeItem(BaseModel):
    scope: str
    count: int


class SectionItem(BaseModel):
    seccion: str | None
    count: int


class ProvinciaItem(BaseModel):
    provincia: str | None
    count: int


class CategoriaItem(BaseModel):
    categoria: str | None
    count: int


class DistritoItem(BaseModel):
    distrito: str | None
    count: int


class OverviewResponse(BaseModel):
    total_articles: int
    total_unique: int
    total_duplicates: int
    duplicate_pct: float
    by_scope: list[ScopeItem]
    by_seccion: list[SectionItem]
    by_provincia: list[ProvinciaItem]
    by_categoria: list[CategoriaItem]
    by_distrito_top15: list[DistritoItem]


class LengthStat(BaseModel):
    mean: float | None
    min: float | None
    max: float | None
    std: float | None
    median: float | None
    mean_words: float | None
    total_rows: int


class LengthsResponse(BaseModel):
    titulo: LengthStat
    subtitulo: LengthStat
    contenido: LengthStat


class WordFrequencyItem(BaseModel):
    word: str
    count: int
    pct: float


class WordFrequencyResponse(BaseModel):
    scope: str
    top: int
    total_articles: int
    words: list[WordFrequencyItem]


class SectionWordFrequency(BaseModel):
    seccion: str | None
    total_articles: int
    words: list[WordFrequencyItem]


class SectionWordFrequencyResponse(BaseModel):
    scope: str
    top: int
    sections: list[SectionWordFrequency]
