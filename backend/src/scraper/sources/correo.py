from src.scraper.sources._arc_rss import ArcXpRssScraper


CORREO_CATEGORY_MAP = {
    "politica": "Política",
    "peru": "Nacional",
    "mundo": "Mundo",
    "deportes": "Deportes",
    "economia": "Economía",
    "espectaculos": "Espectáculos",
    "opinion": "Opinión",
    "lima": "Sociedad",
    "tendencia": "Tendencia",
    "miscelanea": "Tendencia",
}


class CorreoScraper(ArcXpRssScraper):
    SOURCE_ID = 4
    SLUG_FUENTE = "correo"
    BASE_URL = "https://diariocorreo.pe"
    SECTIONS = [
        "politica", "peru", "mundo", "deportes",
        "economia", "espectaculos",
    ]

    @staticmethod
    def _normalize_category(cat: str | None) -> str | None:
        if not cat:
            return None
        key = cat.lower().strip()
        return CORREO_CATEGORY_MAP.get(key, cat.title())
