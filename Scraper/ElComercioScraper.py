import requests
from bs4 import BeautifulSoup
import json
import time
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from collections import Counter

# ─────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────
BASE_URL    = "https://elcomercio.pe"
SLUG_FUENTE = "elcomercio"
ID_FUENTE   = 2
FOCUS_AREAS = ["Lima Metropolitana", "Callao Province"]

# FIX 1 ── Mapeo COMPLETO de secciones de El Comercio.
# 'lima' y 'peru' se normalizan a 'sociedad' (son noticias locales).
# Cualquier segmento que NO esté aquí se DESCARTA.
MAPA_SECCIONES = {
    "lima":             "sociedad",
    "peru":             "sociedad",
    "sociedad":         "sociedad",
    "politica":         "politica",
    "economia":         "economia",
    "negocios":         "economia",
    "mercados":         "economia",
    "deportes":         "deportes",
    "futbol-peruano":   "deportes",
    "mundial":          "deportes",
    "mundo":            "mundo",
    "internacional":    "mundo",
    "tecnologia":       "ciencia",
    "ciencias":         "ciencia",
    "ciencia":          "ciencia",
    "cultura":          "espectaculos",
    "espectaculos":     "espectaculos",
    "entretenimiento":  "espectaculos",
    "opinion":          "opinion",
    "columnistas":      "opinion",
    "ecdata":           "sociedad",
}

SECCIONES_ACEPTADAS = set(MAPA_SECCIONES.values())

# FIX 2 ── Patrones de URL que indican páginas de navegación, perfiles, etc.
PATRONES_URL_BASURA = re.compile(
    r"/autor[es]?/|/tag[s]?/|/search/|/buscar/|/somos/|/archivo/|"
    r"/newsletter|/suscri|/videos?/|/podcast|/especiales?/|"
    r"/interactivos?/|/elecciones-regionales",
    re.IGNORECASE,
)

SEGMENTOS_DESCARTADOS = {
    "autor", "autores", "tag", "tags", "search", "buscar",
    "somos", "archivo", "newsletter", "suscripcion",
    "especiales", "interactivos", "videos", "podcast",
}

# FIX 4 ── Raspar secciones directamente para cubrir deportes, ciencia, etc.
SECCIONES_A_RASPAR = [
    f"{BASE_URL}/lima/",
    f"{BASE_URL}/politica/",
    f"{BASE_URL}/economia/",
    f"{BASE_URL}/deportes/",
    f"{BASE_URL}/futbol-peruano/",
    f"{BASE_URL}/mundo/",
    f"{BASE_URL}/tecnologia/",
    f"{BASE_URL}/cultura/",
    f"{BASE_URL}/espectaculos/",
    f"{BASE_URL}/opinion/",
    f"{BASE_URL}/ciencias/",
]

UBIGEO_DISTRITOS = {
    "miraflores":           "150122",
    "san isidro":           "150131",
    "surco":                "150140",
    "santiago de surco":    "150140",
    "barranco":             "150102",
    "pueblo libre":         "150127",
    "jesus maria":          "150113",
    "san miguel":           "150136",
    "la victoria":          "150117",
    "ate":                  "150102",
    "callao":               "070101",
    "independencia":        "150112",
    "los olivos":           "150121",
    "san martin de porres": "150134",
    "surquillo":            "150141",
    "san borja":            "150130",
    "lince":                "150119",
    "brena":                "150104",
    "carabayllo":           "150106",
    "comas":                "150108",
    "cercado de lima":      "150101",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9",
}


# ─────────────────────────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────────────────────────

def md5(texto):
    return hashlib.md5(texto.encode("utf-8")).hexdigest()

def ahora_iso():
    return datetime.now(timezone.utc).isoformat()

def url_absoluta(url):
    if not url:
        return ""
    return url if url.startswith("http") else urljoin(BASE_URL, url)


def es_url_articulo_valida(url):
    """
    FIX 1 + FIX 2 combinados.
    Devuelve True solo si la URL corresponde a un artículo real de una
    sección aceptada, y no es una página de navegación/perfil/archivo.
    """
    if not url.startswith(BASE_URL):
        return False
    if PATRONES_URL_BASURA.search(url):
        return False

    path = urlparse(url).path.rstrip("/")
    partes = [p for p in path.split("/") if p]

    # Necesita al menos sección + subsección/slug
    if len(partes) < 2:
        return False

    # El primer segmento debe ser una sección conocida
    if partes[0].lower() not in MAPA_SECCIONES:
        return False

    # Ningún segmento puede ser de navegación
    if any(p.lower() in SEGMENTOS_DESCARTADOS for p in partes):
        return False

    # El slug final debe ser suficientemente largo para ser un artículo
    if len(partes[-1]) < 15:
        return False

    return True


def extraer_seccion(url):
    """Devuelve (seccion_raw, seccion_normalizada)."""
    partes = [p for p in urlparse(url).path.split("/") if p]
    if partes:
        raw = partes[0].lower()
        return raw, MAPA_SECCIONES.get(raw, "unknown")
    return "unknown", "unknown"


def limpiar_autor(texto):
    """
    FIX 3 ── El Comercio pega la hora al nombre con el separador '·'.
    Ejemplo: 'Melvyn Arce Ruiz·12:15hs' → 'Melvyn Arce Ruiz'
    """
    texto = texto.split("·")[0]  # Cortar en el punto medio
    for sufijo in ["EscucharResumenCompartir", "Escuchar", "Compartir", "Resumen"]:
        texto = texto.replace(sufijo, "")
    return texto.strip()


def extraer_distrito_y_ubigeo(texto):
    texto_lower = texto.lower()
    for distrito, ubigeo in UBIGEO_DISTRITOS.items():
        if distrito in texto_lower:
            return distrito.title(), ubigeo
    return None, None


# ─────────────────────────────────────────────────────────────────
#  SCRAPING
# ─────────────────────────────────────────────────────────────────

def obtener_pagina(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, "html.parser")
    except requests.RequestException as e:
        print(f"  [ERROR] {url}: {e}")
        return None


def enriquecer_con_metatags(soup, articulo):
    """Mejora campos con Open Graph y meta tags de la página del artículo."""
    og = lambda prop: (soup.find("meta", property=prop) or {}).get("content", "").strip()

    if og("og:title"):
        articulo["titulo"] = og("og:title")
    if og("og:description") and not articulo["subtitulo"]:
        articulo["subtitulo"] = og("og:description")[:400]
    if og("og:image") and not articulo["url_imagen"]:
        articulo["url_imagen"] = og("og:image")

    for prop in ["article:published_time", "pubdate", "date"]:
        meta = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if meta and meta.get("content"):
            articulo["fecha_publicacion"] = meta["content"].strip()
            break

    meta_autor = soup.find("meta", attrs={"name": "author"})
    if meta_autor and meta_autor.get("content") and not articulo["autor"]:
        articulo["autor"] = limpiar_autor(meta_autor["content"])

    return articulo


def extraer_articulo(elemento):
    """Extrae y valida los campos de un artículo desde un elemento HTML."""
    link = elemento if elemento.name == "a" else elemento.find("a", href=True)
    if not link or not link.get("href"):
        return None

    url = url_absoluta(link["href"])

    # Validar URL antes de procesar cualquier cosa
    if not es_url_articulo_valida(url):
        return None

    seccion_raw, seccion_norm = extraer_seccion(url)
    if seccion_norm not in SECCIONES_ACEPTADAS or seccion_norm == "unknown":
        return None

    # Título
    titulo_elem = elemento.find(["h1", "h2", "h3", "h4"])
    titulo = (titulo_elem or link).get_text(strip=True)
    if not titulo or len(titulo) < 10:
        return None

    # Subtítulo — limpiar el patrón "título | subtítulo" de El Comercio
    subtitulo = ""
    for sel in ["p", ".summary", ".excerpt", ".bajada", ".lead"]:
        elem = elemento.select_one(sel)
        if elem:
            t = elem.get_text(strip=True)
            if len(t) > 20 and t != titulo:
                subtitulo = t.split(" | ", 1)[-1][:400]
                break

    # Imagen (lazy-loaded con data-src)
    img = elemento.find("img")
    img_url = ""
    if img:
        img_url = url_absoluta(img.get("data-src") or img.get("src") or "")

    # Autor (FIX 3)
    autor = ""
    for sel in [".author", ".autor", "[class*='author']", "[class*='firma']"]:
        elem = elemento.select_one(sel)
        if elem:
            autor = limpiar_autor(elem.get_text(strip=True))
            break

    # Geografía
    distrito, ubigeo = extraer_distrito_y_ubigeo(f"{titulo} {subtitulo}")

    ts = ahora_iso()
    return {
        "url_original":        url,
        "titulo":              titulo,
        "scope_geografico":    "lima_metropolitana",
        "idioma":              "es",
        "es_duplicado":        False,
        "id_fuente":           ID_FUENTE,
        "slug_fuente":         SLUG_FUENTE,
        "url_canonica":        url,
        "url_imagen":          img_url,
        "subtitulo":           subtitulo,
        "autor":               autor,
        "seccion_fuente":      seccion_raw,
        "seccion_normalizada": seccion_norm,
        "categoria_principal": None,
        "provincia":           "Lima",
        "distrito":            distrito,
        "ubigeo":              ubigeo,
        "fecha_publicacion":   None,
        "fecha_actualizacion": None,
        "hash_titulo":         md5(titulo),
        "hash_contenido":      md5(subtitulo or url),
        "id_noticia_canonica": None,
        "created_at":          ts,
        "updated_at":          ts,
        "_content_preview":    f"{titulo}. {subtitulo}"[:300],
    }


def scrape_elcomercio(modo_detallado=False, limite=150):
    """
    Raspa El Comercio sección por sección (FIX 4).
    Cubre deportes, espectáculos, ciencia y todas las secciones del proyecto.

    Parámetros:
        modo_detallado : Hace un 2do request por artículo para mejorar
                         fecha, autor e imagen. Más lento, más completo.
        limite         : Máximo de artículos únicos a devolver.
    """
    urls_vistas   = set()
    hashes_vistos = set()
    articulos     = []

    selectores = ["article", "[class*='story']", "[class*='card']",
                  "[class*='news-item']", ".listing-item", ".entry"]

    for url_sec in SECCIONES_A_RASPAR:
        if len(articulos) >= limite:
            break

        print(f"\n[SECCIÓN] {url_sec}")
        soup = obtener_pagina(url_sec)
        if not soup:
            continue

        # Buscar elementos con artículos
        elementos = []
        for sel in selectores:
            encontrados = soup.select(sel)
            if encontrados:
                elementos = encontrados
                break
        if not elementos:
            elementos = soup.find_all("a", href=True)  # fallback

        n_sec = 0
        for elem in elementos:
            if len(articulos) >= limite:
                break

            art = extraer_articulo(elem)
            if not art:
                continue

            url = art["url_canonica"]
            if url in urls_vistas:
                continue
            urls_vistas.add(url)

            if art["hash_titulo"] in hashes_vistos:
                art["es_duplicado"] = True
            else:
                hashes_vistos.add(art["hash_titulo"])

            if modo_detallado and not art["es_duplicado"]:
                time.sleep(0.8)
                pagina = obtener_pagina(url)
                if pagina:
                    art = enriquecer_con_metatags(pagina, art)

            articulos.append(art)
            n_sec += 1
            print(f"  ✓ [{len(articulos):03d}][{art['seccion_normalizada']}] {art['titulo'][:65]}...")

        print(f"  → {n_sec} artículos válidos")
        time.sleep(1.2)

    return articulos


# ─────────────────────────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  Scraper El Comercio v2 — NotiBot")
    print("  Fixes: URLs basura · secciones · autor con hora · cobertura")
    print("=" * 65)

    articulos = scrape_elcomercio(modo_detallado=True, limite=150)

    if not articulos:
        print("\n[AVISO] No se encontraron artículos.")
        return

    hoy = datetime.now().strftime("%Y-%m-%d")
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")

    salida = {
        "source":               "El Comercio",
        "slug_fuente":          SLUG_FUENTE,
        "scraped_at":           ahora_iso(),
        "date_range":           {"start": "2026-01-01", "end": hoy},
        "focus_areas":          FOCUS_AREAS,
        "total_articles_found": len(articulos),
        "articles":             articulos,
    }

    nombre = f"elcomercio_news_{ts}.json"
    with open(nombre, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    secciones  = Counter(a["seccion_normalizada"] for a in articulos if not a["es_duplicado"])
    duplicados = sum(1 for a in articulos if a["es_duplicado"])

    print(f"\n{'=' * 65}")
    print(f"  Total artículos : {len(articulos)}")
    print(f"  Duplicados      : {duplicados}")
    print(f"  Por sección:")
    for sec, cnt in secciones.most_common():
        print(f"    {sec:<20} {cnt}")
    print(f"  Guardado en     : {nombre}")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()