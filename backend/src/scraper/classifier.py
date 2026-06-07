import re
import unicodedata


DISTRICT_UBIGEO: dict[str, tuple[str, str]] = {
    "ancon": ("Lima", "150102"),
    "ate": ("Lima", "150103"),
    "barranco": ("Lima", "150104"),
    "breña": ("Lima", "150105"),
    "carabayllo": ("Lima", "150106"),
    "chaclacayo": ("Lima", "150107"),
    "chorrillos": ("Lima", "150108"),
    "cieneguilla": ("Lima", "150109"),
    "comas": ("Lima", "150110"),
    "el agustino": ("Lima", "150111"),
    "independencia": ("Lima", "150112"),
    "jesus maria": ("Lima", "150113"),
    "la molina": ("Lima", "150114"),
    "la victoria": ("Lima", "150115"),
    "lince": ("Lima", "150116"),
    "los olivos": ("Lima", "150117"),
    "lurigancho": ("Lima", "150118"),
    "lurin": ("Lima", "150119"),
    "magdalena del mar": ("Lima", "150120"),
    "miraflores": ("Lima", "150122"),
    "pachacamac": ("Lima", "150123"),
    "pucusana": ("Lima", "150124"),
    "pueblo libre": ("Lima", "150121"),
    "puente piedra": ("Lima", "150125"),
    "punta hermosa": ("Lima", "150126"),
    "punta negra": ("Lima", "150127"),
    "rimac": ("Lima", "150128"),
    "san bartolo": ("Lima", "150129"),
    "san borja": ("Lima", "150130"),
    "san isidro": ("Lima", "150131"),
    "san juan de lurigancho": ("Lima", "150132"),
    "san juan de miraflores": ("Lima", "150133"),
    "san luis": ("Lima", "150134"),
    "san martin de porres": ("Lima", "150135"),
    "san miguel": ("Lima", "150136"),
    "santa anita": ("Lima", "150137"),
    "santa maria del mar": ("Lima", "150138"),
    "santa rosa": ("Lima", "150139"),
    "santiago de surco": ("Lima", "150140"),
    "surco": ("Lima", "150140"),
    "surquillo": ("Lima", "150141"),
    "villa el salvador": ("Lima", "150142"),
    "villa maria del triunfo": ("Lima", "150143"),
    "cercado de lima": ("Lima", "150101"),
    "callao": ("Callao", "070101"),
    "bellavista": ("Callao", "070102"),
    "carmen de la legua reynoso": ("Callao", "070103"),
    "la perla": ("Callao", "070104"),
    "la punta": ("Callao", "070105"),
    "ventanilla": ("Callao", "070106"),
    "mi peru": ("Callao", "070107"),
}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def prepare_keywords(keywords: list[str]) -> list[re.Pattern]:
    patterns = []
    for kw in set(keywords):
        norm = normalize_text(kw)
        patterns.append(re.compile(r"\b" + re.escape(norm) + r"\b"))
    return patterns


def build_district_patterns() -> dict[str, tuple[str, str, str]]:
    return {
        normalize_text(k): (v[0], k, v[1])
        for k, v in DISTRICT_UBIGEO.items()
    }
