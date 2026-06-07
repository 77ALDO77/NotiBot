SECTION_CATEGORY_MAP = {
    "sociedad": "Sociedad", "politica": "Política", "deportes": "Deportes",
    "economia": "Economía", "espectaculos": "Espectáculos", "entretenimiento": "Espectáculos",
    "opinion": "Opinión", "mundo": "Mundo", "ciencia": "Ciencia",
    "datos-lr": "Datos", "verificador": "Datos",
    "lima": "Lima",
}


def infer_categoria(seccion: str | None) -> str | None:
    if not seccion:
        return None
    sec = seccion.lower().strip()
    for key, val in SECTION_CATEGORY_MAP.items():
        if key in sec:
            return val
    return seccion.title()
