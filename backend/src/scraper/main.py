"""
Lima & Callao News Scraper — La República
Scrapes articles from La República sitemaps and maps each one to the
`noticias` table schema in the database.
"""

import argparse
import concurrent.futures
import hashlib
import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ---------------------------------------------------------------------------
# Data model — mirrors the `noticias` table
# ---------------------------------------------------------------------------

@dataclass
class NoticiaRecord:
    """Maps 1-to-1 with the `noticias` database table."""

    # Required / non-optional columns
    url_original: str
    titulo: str
    scope_geografico: str = "desconocido"   # lima_metropolitana | callao | desconocido
    idioma: str = "es"
    es_duplicado: bool = False

    # Source metadata
    id_fuente: Optional[int] = None
    slug_fuente: Optional[str] = None

    # URLs
    url_canonica: Optional[str] = None
    url_imagen: Optional[str] = None

    # Article content metadata
    subtitulo: Optional[str] = None
    autor: Optional[str] = None
    seccion_fuente: Optional[str] = None
    categoria_principal: Optional[str] = None

    # Geographic
    provincia: Optional[str] = None
    distrito: Optional[str] = None
    ubigeo: Optional[str] = None

    # Dates
    fecha_publicacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None

    # Dedup hashes
    hash_titulo: Optional[str] = None
    hash_contenido: Optional[str] = None

    # Canonical duplicate tracking
    id_noticia_canonica: Optional[int] = None

    # Audit timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Auto-compute hashes after object creation."""
        if self.titulo and self.hash_titulo is None:
            self.hash_titulo = hashlib.sha256(self.titulo.encode()).hexdigest()[:32]


def noticia_to_dict(record: NoticiaRecord, contenido: str = "") -> dict:
    """Serialize a NoticiaRecord to a JSON-safe dict.

    Also computes hash_contenido here so that the raw content string
    does not need to be stored on the dataclass itself.
    """
    d = asdict(record)

    # Compute content hash if not already set
    if not d.get("hash_contenido") and contenido:
        d["hash_contenido"] = hashlib.sha256(contenido.encode()).hexdigest()[:32]

    # Serialize datetime fields to ISO-8601 strings
    for key in ("fecha_publicacion", "fecha_actualizacion", "created_at", "updated_at"):
        val = d.get(key)
        if isinstance(val, datetime):
            d[key] = val.isoformat()
        elif val is None:
            d[key] = None

    return d


# ---------------------------------------------------------------------------
# District → ubigeo mapping (Lima Metropolitana + Callao)
# ---------------------------------------------------------------------------

DISTRICT_UBIGEO: dict[str, tuple[str, str]] = {
    # --- Lima Metropolitana ---
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
    # --- Callao ---
    "callao": ("Callao", "070101"),
    "bellavista": ("Callao", "070102"),
    "carmen de la legua reynoso": ("Callao", "070103"),
    "la perla": ("Callao", "070104"),
    "la punta": ("Callao", "070105"),
    "ventanilla": ("Callao", "070106"),
    "mi peru": ("Callao", "070107"),
}


# ---------------------------------------------------------------------------
# Main scraper class
# ---------------------------------------------------------------------------

class LimaCallaoNewsScraper:
    SOURCE_ID = 1
    SLUG_FUENTE = "larepublica"

    def __init__(
        self,
        start_date_str: str = "2026-01-01",
        end_date_str: Optional[str] = None,
        max_workers: int = 5,
    ):
        if end_date_str is None:
            end_date_str = datetime.now().strftime("%Y-%m-%d")

        try:
            self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            self.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                f"Error parsing dates: {exc}. Use YYYY-MM-DD format."
            ) from exc

        self.start_date_str = start_date_str
        self.end_date_str = end_date_str
        self.max_workers = max_workers
        self.session = self._setup_session()

        # Keyword patterns for geographic scope detection
        self.lima_keywords = self._prepare_keywords([
            "lima", "lima metropolitana", "metropolitana de lima",
            "cono norte", "cono sur", "cono este", "cono oeste",
            "san miguel", "san isidro", "miraflores", "barranco",
            "surco", "la molina", "santiago de surco", "jesus maria",
            "lince", "pueblo libre", "breña", "cercado de lima",
            "rimac", "el agustino", "independencia", "comas",
            "carabayllo", "puente piedra", "los olivos", "ancon",
            "santa rosa", "chaclacayo", "lurigancho", "lurin",
            "pachacamac", "pucusana", "san bartolo",
            "san juan de lurigancho", "san juan de miraflores",
            "villa maria del triunfo", "villa el salvador",
            "magdalena del mar", "san borja", "surquillo",
            "san martin de porres", "ate", "la victoria",
            "chorrillos", "santa anita", "san luis",
        ])

        self.callao_keywords = self._prepare_keywords([
            "callao", "provincia constitucional del callao",
            "bellavista", "carmen de la legua reynoso", "la perla",
            "ventanilla", "mi peru", "la punta",
        ])

        # Normalised district names for ubigeo lookup
        self._district_patterns = {
            self._normalize_text(k): (v[0], k, v[1])   # (provincia, distrito, ubigeo)
            for k, v in DISTRICT_UBIGEO.items()
        }

    # ------------------------------------------------------------------
    # Session setup
    # ------------------------------------------------------------------

    def _setup_session(self) -> requests.Session:
        """Configure a requests session with retries and pooling."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-PE,es;q=0.9",
        })
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(
            max_retries=retries, pool_connections=10, pool_maxsize=20
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # ------------------------------------------------------------------
    # Text utilities
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        """Lowercase + strip diacritics."""
        if not text:
            return ""
        text = str(text).lower()
        return "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )

    def _prepare_keywords(self, keywords: list[str]) -> list[re.Pattern]:
        """Compile whole-word regex patterns for each keyword."""
        patterns = []
        for kw in set(keywords):
            norm = self._normalize_text(kw)
            patterns.append(re.compile(r"\b" + re.escape(norm) + r"\b"))
        return patterns

    # ------------------------------------------------------------------
    # Sitemap discovery
    # ------------------------------------------------------------------

    def get_sitemaps(self) -> list[str]:
        return [
            "https://larepublica.pe/sitemap.xml",
        ]

    def parse_sitemap(self, sitemap_url: str) -> list[dict]:
        """Return list of {url, lastmod} dicts within the configured date range."""
        try:
            resp = self.session.get(sitemap_url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  [WARN] Could not fetch sitemap {sitemap_url}: {exc}")
            return []

        try:
            root = ET.fromstring(resp.content)
            ns = {
                "": "http://www.sitemaps.org/schemas/sitemap/0.9",
                "news": "http://www.google.com/schemas/sitemap-news/0.9",
            }
            urls = []
            for url_elem in root.findall(".//url", ns):
                loc_elem = url_elem.find("loc", ns)
                lastmod_elem = url_elem.find("lastmod", ns)

                if loc_elem is None or not loc_elem.text:
                    continue

                url = loc_elem.text.strip()
                lastmod = None
                if lastmod_elem is not None and lastmod_elem.text:
                    lastmod = self._parse_date_flexible(lastmod_elem.text)

                if lastmod and self.start_date <= lastmod.date() <= self.end_date:
                    urls.append({"url": url, "lastmod": lastmod})

            return urls
        except ET.ParseError as exc:
            print(f"  [WARN] XML parse error for {sitemap_url}: {exc}")
            return []

    @staticmethod
    def _parse_date_flexible(date_str: str) -> Optional[datetime]:
        """Try several common date formats and return a datetime or None."""
        date_str = date_str.strip()
        for fmt in (
            # ISO-8601 with timezone
            lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
            # ISO date only
            lambda s: datetime.strptime(s[:10], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ),
        ):
            try:
                return fmt(date_str)
            except (ValueError, TypeError):
                continue
        return None

    # ------------------------------------------------------------------
    # Article extraction
    # ------------------------------------------------------------------

    def extract_article_content(self, url: str) -> Optional[dict]:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            return None

        soup = BeautifulSoup(resp.content, "html.parser")

        json_ld = self._extract_json_ld(soup)

        titulo = (
            json_ld.get("headline")
            or self._meta(soup, "og:title")
            or (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
            or (soup.find("title").get_text(strip=True) if soup.find("title") else "")
        ).strip()

        subtitulo = (
            json_ld.get("description")
            or self._meta(soup, "og:description")
            or self._meta(soup, "description")
        )
        if subtitulo:
            subtitulo = subtitulo.strip()

        autor = None
        if "author" in json_ld:
            author_raw = json_ld["author"]
            if isinstance(author_raw, list):
                autor = ", ".join(
                    a.get("name", "") for a in author_raw if isinstance(a, dict)
                )
            elif isinstance(author_raw, dict):
                autor = author_raw.get("name")
            elif isinstance(author_raw, str):
                autor = author_raw
        if not autor:
            for sel in (
                '[class*="author"]',
                '[class*="byline"]',
                '[rel="author"]',
                ".firma",
            ):
                el = soup.select_one(sel)
                if el:
                    autor = el.get_text(strip=True)
                    break

        url_canonica = (
            json_ld.get("url")
            or json_ld.get("mainEntityOfPage", {}).get("@id")
            or self._meta(soup, "og:url")
        )
        canon_tag = soup.find("link", rel="canonical")
        if not url_canonica and canon_tag:
            url_canonica = canon_tag.get("href")

        url_imagen = (
            json_ld.get("image", {}).get("url")
            if isinstance(json_ld.get("image"), dict)
            else json_ld.get("image")
        )
        if not url_imagen:
            url_imagen = self._meta(soup, "og:image")

        fecha_publicacion = self._parse_date_flexible(
            json_ld.get("datePublished", "")
            or self._meta(soup, "article:published_time", "")
        )
        fecha_actualizacion = self._parse_date_flexible(
            json_ld.get("dateModified", "")
            or self._meta(soup, "article:modified_time", "")
        )
        if not fecha_publicacion:
            for sel in (
                'time[itemprop="datePublished"]',
                'time[class*="publish"]',
                "time[datetime]",
            ):
                el = soup.select_one(sel)
                if el:
                    fecha_publicacion = self._parse_date_flexible(
                        el.get("datetime", "") or el.get_text(strip=True)
                    )
                    if fecha_publicacion:
                        break

        path_parts = [p for p in urlparse(url).path.split("/") if p]
        seccion_fuente = path_parts[0] if path_parts else None

        categoria_principal = None
        if "articleSection" in json_ld:
            raw = json_ld["articleSection"]
            categoria_principal = raw[0] if isinstance(raw, list) else raw

        content = self._extract_body(soup)
        content_html = self._extract_body_html(soup)

        return {
            "url": url,
            "url_canonica": url_canonica or url,
            "url_imagen": url_imagen,
            "titulo": titulo,
            "subtitulo": subtitulo,
            "autor": autor,
            "seccion_fuente": seccion_fuente,
            "categoria_principal": categoria_principal,
            "fecha_publicacion": fecha_publicacion,
            "fecha_actualizacion": fecha_actualizacion,
            "content": content,
            "contenido_html": content_html,
            "contenido_crudo": resp.text,
            "raw_jsonld": json_ld if json_ld else None,
            "raw_metadata": self._extract_all_meta(soup),
        }

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_ld(soup: BeautifulSoup) -> dict:
        """Return the first NewsArticle / Article JSON-LD block found."""
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, list):
                    data = next(
                        (d for d in data if d.get("@type") in ("NewsArticle", "Article")),
                        {},
                    )
                if data.get("@type") in ("NewsArticle", "Article"):
                    return data
            except (json.JSONDecodeError, AttributeError):
                continue
        return {}

    @staticmethod
    def _meta(soup: BeautifulSoup, prop: str, default: str = "") -> str:
        """Get <meta> content by property or name attribute."""
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        return (tag.get("content", default) if tag else default) or default

    @staticmethod
    def _extract_body(soup: BeautifulSoup) -> str:
        """Extract article body text."""
        for sel in (
            '[class*="article-body"]',
            '[class*="article-content"]',
            '[class*="post-content"]',
            '[itemprop="articleBody"]',
            "article",
        ):
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 150:
                    return text

        # Fallback: collect substantial <p> tags
        return " ".join(
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 30
        )

    @staticmethod
    def _extract_body_html(soup: BeautifulSoup) -> Optional[str]:
        for sel in (
            '[class*="article-body"]',
            '[class*="article-content"]',
            '[class*="post-content"]',
            '[itemprop="articleBody"]',
            "article",
        ):
            el = soup.select_one(sel)
            if el:
                html = str(el)
                if len(html) > 100:
                    return html
        return None

    @staticmethod
    def _extract_all_meta(soup: BeautifulSoup) -> dict:
        meta = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name")
            content = tag.get("content")
            if prop and content:
                meta[prop] = content
        return meta if meta else None

    # ------------------------------------------------------------------
    # Geographic classification
    # ------------------------------------------------------------------

    def classify_geo(self, titulo: str, content: str) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
        """Classify the article's geographic scope.

        Returns (scope_geografico, provincia, distrito, ubigeo).
        """
        text = self._normalize_text(titulo + " " + content)

        # Detect most specific district first
        for norm_district, (provincia, raw_district, ubigeo) in self._district_patterns.items():
            if re.search(r"\b" + re.escape(norm_district) + r"\b", text):
                scope = (
                    "lima_metropolitana" if provincia == "Lima" else "callao"
                )
                return scope, provincia, raw_district.title(), ubigeo

        # Broad Lima check
        for pattern in self.lima_keywords:
            if pattern.search(text):
                return "lima_metropolitana", "Lima", None, None

        # Broad Callao check
        for pattern in self.callao_keywords:
            if pattern.search(text):
                return "callao", "Callao", None, None

        return "desconocido", None, None, None

    # ------------------------------------------------------------------
    # Article processing
    # ------------------------------------------------------------------

    def process_article(self, article_info: dict) -> Optional[tuple[NoticiaRecord, dict]]:
        url = article_info["url"]
        data = self.extract_article_content(url)

        if not data or not data.get("titulo"):
            return None

        scope, provincia, distrito, ubigeo = self.classify_geo(
            data["titulo"], data["content"]
        )

        if scope == "desconocido":
            return None

        record = NoticiaRecord(
            id_fuente=self.SOURCE_ID,
            slug_fuente=self.SLUG_FUENTE,
            url_original=url,
            url_canonica=data["url_canonica"],
            url_imagen=data["url_imagen"],
            titulo=data["titulo"],
            subtitulo=data["subtitulo"],
            autor=data["autor"],
            seccion_fuente=data["seccion_fuente"],
            categoria_principal=data["categoria_principal"] or _infer_categoria(data["seccion_fuente"]),
            scope_geografico=scope,
            provincia=provincia,
            distrito=distrito,
            ubigeo=ubigeo,
            fecha_publicacion=data["fecha_publicacion"],
            fecha_actualizacion=data["fecha_actualizacion"],
            idioma="es",
            es_duplicado=False,
        )

        contenido_data = {
            "titulo_extraido": data.get("titulo"),
            "bajada_extraida": data.get("subtitulo"),
            "contenido_crudo": data.get("contenido_crudo"),
            "contenido_limpio": data["content"],
            "contenido_html": data.get("contenido_html"),
            "raw_jsonld": data.get("raw_jsonld"),
            "raw_metadata": data.get("raw_metadata"),
            "calidad_extraccion": "valida" if data["content"] else "sin_validar",
        }
        return record, contenido_data

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run(self) -> list[tuple[NoticiaRecord, str]]:
        """Crawl all sitemaps and return a list of (record, body_text) tuples."""
        print(f"Scraping range: {self.start_date_str} → {self.end_date_str}")
        print("Focus: Lima Metropolitana + Callao Province\n")

        sitemaps = self.get_sitemaps()
        print(f"Fetching {len(sitemaps)} sitemaps...")

        article_infos: list[dict] = []
        for i, sm_url in enumerate(sitemaps, 1):
            print(f"  [{i}/{len(sitemaps)}] {sm_url}")
            article_infos.extend(self.parse_sitemap(sm_url))
            time.sleep(0.5)

        print(f"\nFound {len(article_infos)} articles in date range")
        print(f"Processing with {self.max_workers} threads...\n")

        results: list[tuple[NoticiaRecord, dict]] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.process_article, info): info
                for info in article_infos
            }
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                if completed % 50 == 0:
                    print(f"  Progress: {completed}/{len(article_infos)}")
                try:
                    result = future.result()
                    if result:
                        record, body = result
                        results.append((record, body))
                        label = (
                            f"[{record.scope_geografico}]"
                            + (f" {record.distrito}" if record.distrito else "")
                        )
                        print(f"  ✓ {label}: {record.titulo[:60]}")
                except Exception as exc:
                    print(f"  ✗ Error: {exc}")

        return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="La República News Scraper — Lima Metropolitana & Callao"
    )
    parser.add_argument(
        "--start", type=str, default="2026-01-01", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD), defaults to today",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Scrape a single specific date (YYYY-MM-DD). Overrides --start and --end.",
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="Scrape only today's date. Overrides --start, --end, and --date.",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Iterate day by day within the date range. Logs each day independently.",
    )
    parser.add_argument(
        "--workers", type=int, default=5, help="Concurrent worker threads"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON filename (auto-generated if omitted)",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="Write results to database (reads DATABASE_URL from .env or env var)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only output JSON, skip database (default if --db not set)",
    )
    args = parser.parse_args()

    if args.today:
        today_str = datetime.now().strftime("%Y-%m-%d")
        args.date = today_str
        args.daily = True

    if args.date:
        args.start = args.date
        args.end = args.date

    print("=" * 60)
    print("La República News Scraper — Lima Metropolitana & Callao")
    print("=" * 60)

    if args.daily:
        _run_daily(args)
    else:
        _run_batch(args)


def _run_batch(args):
    scraper = LimaCallaoNewsScraper(
        start_date_str=args.start,
        end_date_str=args.end,
        max_workers=args.workers,
    )

    results = scraper.run()
    _save_and_report(results, args, scraper)


def _scrape_elcomercio_day(session: requests.Session, date_str: str, max_workers: int = 3,
                            classifier: LimaCallaoNewsScraper | None = None) -> list[tuple[NoticiaRecord, dict]]:
    import concurrent.futures
    from src.scraper.sources.elcomercio import ElComercioScraper

    ec = ElComercioScraper(session)
    sitemaps = ec.get_sitemap_index_urls()

    article_infos: list[dict] = []
    for sm_url in sitemaps[:2]:
        article_infos.extend(ec.parse_sitemap(sm_url))

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    results: list[tuple[NoticiaRecord, dict]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for info in article_infos:
            if info.get("lastmod") and info["lastmod"].date() == target_date:
                futures[executor.submit(ec.extract_article, info["url"])] = info

        for future in concurrent.futures.as_completed(futures):
            try:
                data = future.result()
                if data and data.get("titulo"):
                    scope_geo = "desconocido"
                    provincia = None
                    distrito = None
                    ubigeo = None
                    if classifier:
                        scope_geo, provincia, distrito, ubigeo = classifier.classify_geo(
                            data["titulo"], data.get("content", "")
                        )

                    record = NoticiaRecord(
                        id_fuente=ElComercioScraper.SOURCE_ID,
                        slug_fuente=ElComercioScraper.SLUG_FUENTE,
                        url_original=data["url"],
                        url_canonica=data.get("url_canonica"),
                        url_imagen=data.get("url_imagen"),
                        titulo=data["titulo"],
                        subtitulo=data.get("subtitulo"),
                        autor=data.get("autor"),
                        seccion_fuente=data.get("seccion_fuente"),
                        categoria_principal=data.get("categoria_principal") or _infer_categoria(data.get("seccion_fuente")),
                        scope_geografico=scope_geo,
                        provincia=provincia,
                        distrito=distrito,
                        ubigeo=ubigeo,
                        fecha_publicacion=data.get("fecha_publicacion"),
                        fecha_actualizacion=data.get("fecha_actualizacion"),
                        idioma="es",
                        es_duplicado=False,
                    )
                    contenido_data = {
                        "titulo_extraido": data.get("titulo"),
                        "bajada_extraida": data.get("subtitulo"),
                        "contenido_crudo": data.get("contenido_crudo"),
                        "contenido_limpio": data["content"],
                        "contenido_html": data.get("contenido_html"),
                        "raw_jsonld": data.get("raw_jsonld"),
                        "raw_metadata": data.get("raw_metadata"),
                        "calidad_extraccion": "valida" if data["content"] else "sin_validar",
                    }
                    results.append((record, contenido_data))
                    print(f"  ✓ [EC] {record.titulo[:60]}")
            except Exception as e:
                print(f"  ✗ [EC Error]: {e}")

    return results


def _run_daily(args):
    from datetime import date, timedelta

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else date.today()
    current = start

    all_results: list[tuple[NoticiaRecord, dict]] = []

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        print(f"\n{'─' * 40}")
        print(f"DIA: {date_str}")
        print(f"{'─' * 40}")

        scraper = LimaCallaoNewsScraper(
            start_date_str=date_str,
            end_date_str=date_str,
            max_workers=args.workers,
        )

        results = scraper.run()
        all_results.extend(results)

        urls_totales = len([info for sm in scraper.get_sitemaps() 
                           for info in scraper.parse_sitemap(sm)])

        if args.db and results:
            db_written, db_errors = _write_to_database_daily(results, scraper, date_str, urls_totales)
            print(f"  DB LaRepublica: {db_written} insertadas, {db_errors} errores")
        else:
            print(f"  LaRepublica: {len(results)} encontrados")

        ec_results = _scrape_elcomercio_day(scraper.session, date_str, args.workers, scraper)
        all_results.extend(ec_results)
        if args.db and ec_results:
            ec_written, ec_errors = _write_to_database_daily(
                ec_results, scraper, date_str,
                urls_totales=len(ec_results), source_slug="elcomercio"
            )
            print(f"  DB ElComercio: {ec_written} insertadas, {ec_errors} errores")
        else:
            print(f"  ElComercio: {len(ec_results)} encontrados")

        current += timedelta(days=1)

    _save_json(all_results, args, scraper)

    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE (modo daily)")
    print("=" * 60)
    print(f"Total articulos: {len(all_results)}")
    print(f"Dias procesados: {(end_date - start).days + 1}")


def _save_and_report(results, args, scraper):
    _save_json(results, args, scraper)

    db_written = 0
    db_errors = 0
    if args.db and results:
        db_written, db_errors = _write_to_database(results, scraper.get_sitemaps())

    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    print(f"Total articles found : {len(results)}")
    if args.db:
        print(f"DB records inserted  : {db_written}")
        if db_errors:
            print(f"DB errors            : {db_errors}")

    lima_count = sum(1 for r, _ in results if r.scope_geografico == "lima_metropolitana")
    callao_count = sum(1 for r, _ in results if r.scope_geografico == "callao")
    print(f"\nBreakdown:")
    print(f"  Lima Metropolitana : {lima_count}")
    print(f"  Callao Province    : {callao_count}")

    if results:
        print("\nSample articles:")
        for i, (record, _) in enumerate(results[:3], 1):
            loc = f"[{record.scope_geografico}" + (
                f" / {record.distrito}]" if record.distrito else "]"
            )
            print(f"  {i}. {loc} {record.titulo}")
            print(f"     {record.url_original}")


def _save_json(results, args, scraper):
    articles_json = []
    for record, contenido_data in results:
        row = noticia_to_dict(record, contenido=contenido_data.get("contenido_limpio", ""))
        row["_content_preview"] = (
            contenido_data.get("contenido_limpio", "")[:500] + "\u2026"
            if len(contenido_data.get("contenido_limpio", "")) > 500
            else contenido_data.get("contenido_limpio", "")
        )
        articles_json.append(row)

    output = {
        "source": "La República",
        "slug_fuente": scraper.SLUG_FUENTE,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "date_range": {"start": scraper.start_date_str, "end": scraper.end_date_str},
        "focus_areas": ["Lima Metropolitana", "Callao Province"],
        "total_articles_found": len(results),
        "articles": articles_json,
    }

    filename = args.output or f"data/lima_callao_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"JSON saved to: {filename}")


def _record_to_db_dict(record: NoticiaRecord, contenido: str = "") -> dict:
    import hashlib

    d = {
        "url_original": record.url_original,
        "url_canonica": record.url_canonica,
        "url_imagen": record.url_imagen,
        "slug_fuente": record.slug_fuente,
        "titulo": record.titulo,
        "subtitulo": record.subtitulo,
        "autor": record.autor,
        "seccion_fuente": record.seccion_fuente,
        "categoria_principal": record.categoria_principal,
        "scope_geografico": record.scope_geografico,
        "provincia": record.provincia,
        "distrito": record.distrito,
        "ubigeo": record.ubigeo,
        "fecha_publicacion": record.fecha_publicacion,
        "fecha_actualizacion": record.fecha_actualizacion,
        "hash_titulo": record.hash_titulo,
        "hash_contenido": None,
        "idioma": record.idioma,
        "es_duplicado": record.es_duplicado,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    if not d["hash_titulo"] and record.titulo:
        d["hash_titulo"] = hashlib.sha256(record.titulo.encode()).hexdigest()[:32]
    if contenido:
        d["hash_contenido"] = hashlib.sha256(contenido.encode()).hexdigest()[:32]
    return d


def _write_to_database(results: list[tuple[NoticiaRecord, dict]], sitemaps: list[str]) -> tuple[int, int]:
    import asyncio
    import os

    from src.scraper.db_writer import NewsDBWriter

    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://notibot:notibot_dev_2026@192.168.3.13:5432/notibot")
    db_writer = NewsDBWriter(database_url)
    written = 0
    errors = 0

    async def _do_write():
        nonlocal written, errors
        await db_writer.connect()
        await db_writer.ensure_fuente()

        for sitemap_url in sitemaps:
            await db_writer.ensure_fuente_seed(sitemap_url)

        for record, contenido_data in results:
            try:
                record_dict = _record_to_db_dict(record, contenido_data.get("contenido_limpio", ""))
                noticia_id = await db_writer.insert_noticia(record_dict, contenido_data)
                if noticia_id:
                    written += 1
                    await db_writer.create_chunking_job(noticia_id)
                else:
                    errors += 1
            except Exception as e:
                print(f"  [DB ERROR] {record.titulo[:60]}: {e}")
                errors += 1

        await db_writer.log_scraping(
            "info",
            f"Scraping completed: {written} articles, {errors} errors, {len(results)} total",
        )
        await db_writer.commit()
        await db_writer.close()

    asyncio.run(_do_write())
    return written, errors


SECTION_CATEGORY_MAP = {
    "sociedad": "Sociedad", "politica": "Política", "deportes": "Deportes",
    "economia": "Economía", "espectaculos": "Espectáculos", "entretenimiento": "Espectáculos",
    "opinion": "Opinión", "mundo": "Mundo", "ciencia": "Ciencia",
    "datos-lr": "Datos", "verificador": "Datos",
    "lima": "Lima",
}


def _infer_categoria(seccion: str | None) -> str | None:
    if not seccion:
        return None
    sec = seccion.lower().strip()
    for key, val in SECTION_CATEGORY_MAP.items():
        if key in sec:
            return val
    return seccion.title()


def _write_to_database_daily(results: list[tuple[NoticiaRecord, dict]], scraper, date_str: str,
                              urls_totales: int, source_slug: str = "larepublica") -> tuple[int, int]:
    import asyncio
    import os

    from src.scraper.db_writer import NewsDBWriter

    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://notibot:notibot_dev_2026@192.168.3.13:5432/notibot")
    db_writer = NewsDBWriter(database_url, source_slug=source_slug)
    written = 0
    errors = 0
    duplicadas = 0

    async def _do_write():
        nonlocal written, errors, duplicadas
        await db_writer.connect()
        await db_writer.ensure_fuente()

        for sitemap_url in scraper.get_sitemaps():
            await db_writer.ensure_fuente_seed(sitemap_url)

        await db_writer.log_scraping(
            "info",
            f"Iniciando scraping dia {date_str}: {urls_totales} URLs en sitemaps",
        )

        for record, contenido_data in results:
            try:
                record_dict = _record_to_db_dict(record, contenido_data.get("contenido_limpio", ""))
                noticia_id = await db_writer.insert_noticia(record_dict, contenido_data)
                if noticia_id:
                    written += 1
                    await db_writer.create_chunking_job(noticia_id)
                else:
                    duplicadas += 1
            except Exception as e:
                errors += 1
                await db_writer.log_scraping(
                    "error",
                    f"Error en {record.url_original}: {str(e)[:200]}",
                    meta={"fecha": date_str, "url": record.url_original},
                )

        await db_writer.log_day_summary(
            date_str=date_str,
            urls_totales=urls_totales,
            filtradas_geo=len(results),
            insertadas=written,
            errores=errors,
            duplicadas=duplicadas,
        )
        await db_writer.commit()
        await db_writer.close()

    asyncio.run(_do_write())
    return written, errors


if __name__ == "__main__":
    main()