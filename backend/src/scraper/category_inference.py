SECTION_CATEGORY_MAP = {
    # ── Política ────────────────────────────────────────────
    "politica": "Política",
    "elecciones": "Política",
    "congreso": "Política",
    "gobierno": "Política",
    # ── Sociedad ────────────────────────────────────────────
    "sociedad": "Sociedad",
    "actualidad": "Sociedad",
    "ciudad": "Sociedad",
    "lima": "Sociedad",
    "sucesos": "Sociedad",
    "policiales": "Sociedad",
    "accidentes": "Sociedad",
    "transporte": "Sociedad",
    "obras": "Sociedad",
    "justicia": "Sociedad",
    "salud": "Sociedad",
    "vida": "Sociedad",
    "educacion": "Sociedad",
    "mujer": "Sociedad",
    "tendencia": "Tendencia",
    "tendencias": "Tendencia",
    "miscelanea": "Tendencia",
    # ── Nacional ─────────────────────────────────────────────
    "peru": "Nacional",
    "perú": "Nacional",
    "piura": "Nacional",
    "edicion": "Nacional",
    # ── Deportes ─────────────────────────────────────────────
    "deportes": "Deportes",
    "deporte-total": "Deportes",
    "deporte total": "Deportes",
    # ── Economía ─────────────────────────────────────────────
    "economia": "Economía",
    "economía": "Economía",
    "mercados": "Economía",
    "empresas": "Economía",
    "finanzas-personales": "Economía",
    "finanzas": "Economía",
    "gestion": "Economía",
    # ── Mundo ────────────────────────────────────────────────
    "mundo": "Mundo",
    "internacional": "Mundo",
    "locomundo": "Mundo",
    # ── Espectáculos ─────────────────────────────────────────
    "espectaculos": "Espectáculos",
    "entretenimiento": "Espectáculos",
    "luces": "Espectáculos",
    "musica": "Espectáculos",
    "música": "Espectáculos",
    "cine y series": "Espectáculos",
    # ── Cultura ──────────────────────────────────────────────
    "cultura": "Cultura",
    "cultural": "Cultura",
    # ── Tecnología ───────────────────────────────────────────
    "tecnologia": "Tecnología",
    # ── Opinión ──────────────────────────────────────────────
    "opinion": "Opinión",
    "columnistas": "Opinión",
    # ── Ciencia ──────────────────────────────────────────────
    "ciencia": "Ciencia",
    # ── Datos ────────────────────────────────────────────────
    "datos-lr": "Datos",
    "verificador": "Datos",
    "ecdata": "Datos",
    # ── Historia ─────────────────────────────────────────────
    "archivo el comercio": "Historia",
    "eldominical": "Historia",
    # ── Regiones → Nacional ──────────────────────────────────
    "arequipa": "Nacional",
    "cusco": "Nacional",
    "huancayo": "Nacional",
    "ica": "Nacional",
    "la libertad": "Nacional",
    "piura": "Nacional",
    "puno": "Nacional",
    "san martin": "Nacional",
    "tacna": "Nacional",
    # ── Secciones extra ──────────────────────────────────────
    "g-de-gestion": "Economía",
    "partidos": "Política",
    "curiosidades": "Tendencia",
    "judiciales": "Sociedad",
    "familia": "Sociedad",
    "el informante": "Opinión",
    "especiales": "Tendencia",
}

TITLE_KEYWORDS = {
    "Deportes": [
        "gol", "liga", "mundial", "partido", "selección",
        "fútbol", "tenis", "champions", "fichaje", "entrenador",
        "clasificatoria", "copa", "torneo", "campeonato", "estadio",
    ],
    "Economía": [
        "inflación", "dólar", "pbi", "mercado", "finanzas",
        "bcr", "economía", "exportación", "importación", "tributaria",
        "subsidio", "pensión", "bonos", "afp", "sueldo",
    ],
    "Política": [
        "elecciones", "gobierno", "ministro", "congreso", "presidente",
        "candidato", "votación", "segunda vuelta", "jne", "onpe",
        "debate", "personero", "escrutinio", "mesa de sufragio",
    ],
    "Salud": [
        "vacuna", "hospital", "salud", "covid", "pandemia",
        "sarampión", "epidemia", "contagio", "médico", "paciente",
        "minsa", "essalud", "cirugía", "diagnóstico",
    ],
    "Tecnología": [
        "tecnología", "app", "aplicación", "inteligencia artificial", "ia ",
        "startup", "digital", "software", "robot", "innovación",
    ],
    "Espectáculos": [
        "concierto", "actor", "actriz", "película", "serie",
        "farándula", "instagram", "tiktok", "cantante", "estreno",
    ],
    "Cultura": [
        "museo", "exposición", "festival", "libro", "obra",
        "teatro", "literatura", "patrimonio", "arqueología", "artista",
    ],
    "Mundo": [
        "ee.uu", "onu", "guerra", "conflicto", "europa",
        "asia", "latinoamérica", "crisis", "diplomático", "embajada",
    ],
}


def infer_categoria(seccion: str | None, titulo: str = "") -> str | None:
    if not seccion:
        return None
    sec = seccion.lower().strip()
    for key, val in SECTION_CATEGORY_MAP.items():
        if key in sec:
            return val

    if titulo:
        t = titulo.lower()
        for cat, keywords in TITLE_KEYWORDS.items():
            for kw in keywords:
                if kw in t:
                    return cat

    return seccion.title()
