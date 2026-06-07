from src.scraper.sources._arc_rss import ArcXpRssScraper


OJO_CATEGORY_MAP = {
    "actualidad": "Sociedad",
    "politica": "Política",
    "locomundo": "Mundo",
    "internacional": "Mundo",
    "deportes": "Deportes",
    "ciudad": "Sociedad",
    "mujer": "Espectáculos",
    "columnistas": "Opinión",
    "espectaculos": "Espectáculos",
    "peru": "Nacional",
    "economia": "Economía",
}


class OjoScraper(ArcXpRssScraper):
    SOURCE_ID = 7
    SLUG_FUENTE = "ojo"
    BASE_URL = "https://ojo.pe"
    SECTIONS = [
        "actualidad", "politica", "locomundo",
        "internacional", "ciudad", "mujer", "columnistas",
    ]

    @staticmethod
    def _normalize_category(cat: str | None) -> str | None:
        if not cat:
            return None
        key = cat.lower().strip()
        return OJO_CATEGORY_MAP.get(key, cat.title())
