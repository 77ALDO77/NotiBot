from src.scraper.sources._arc_rss import ArcXpRssScraper


GESTION_CATEGORY_MAP = {
    "economia": "Economía",
    "mercados": "Economía",
    "empresas": "Economía",
    "politica": "Política",
    "peru": "Nacional",
    "mundo": "Mundo",
    "deportes": "Deportes",
    "tecnologia": "Tecnología",
    "opinion": "Opinión",
    "finanzas-personales": "Economía",
    "tendencias": "Tendencia",
    "gestion": "Economía",
}


class GestionScraper(ArcXpRssScraper):
    SOURCE_ID = 5
    SLUG_FUENTE = "gestion"
    BASE_URL = "https://gestion.pe"
    SECTIONS = [
        "economia", "mercados", "politica", "mundo",
        "deportes", "tecnologia",
    ]
