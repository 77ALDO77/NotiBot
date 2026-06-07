from src.scraper.sources._arc_rss import ArcXpRssScraper


TROME_CATEGORY_MAP = {
    "actualidad": "Sociedad",
    "deportes": "Deportes",
    "espectaculos": "Espectáculos",
    "mundo": "Mundo",
    "tendencias": "Tendencia",
    "politica": "Política",
    "economia": "Economía",
    "peru": "Nacional",
    "opinion": "Opinión",
}


class TromeScraper(ArcXpRssScraper):
    SOURCE_ID = 6
    SLUG_FUENTE = "trome"
    BASE_URL = "https://trome.com"
    SECTIONS = [
        "actualidad", "deportes", "espectaculos",
        "mundo", "tendencias",
    ]
