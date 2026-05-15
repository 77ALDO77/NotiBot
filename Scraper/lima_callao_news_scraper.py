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
from typing import Optional
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
            "https://larepublica.pe/sitemap/sociedad.xml",
            "https://larepublica.pe/sitemap/politica.xml",
            "https://larepublica.pe/sitemap/economia.xml",
            "https://larepublica.pe/sitemap/mundo.xml",
            "https://larepublica.pe/sitemap/deportes.xml",
            "https://larepublica.pe/sitemap/espectaculos.xml",
            "https://larepublica.pe/sitemap/ciencia.xml",
            "https://larepublica.pe/sitemap/opinion.xml",
            "https://larepublica.pe/sitemap/datos-lr.xml",
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
        """Fetch and parse a single article URL.

        Returns a dict with all fields needed to build a NoticiaRecord,
        or None on network/parse failure.
        """
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            return None

        soup = BeautifulSoup(resp.content, "html.parser")

        # ---- JSON-LD structured data (most reliable source) ----
        json_ld = self._extract_json_ld(soup)

        # ---- Title ----
        titulo = (
            json_ld.get("headline")
            or self._meta(soup, "og:title")
            or (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
            or (soup.find("title").get_text(strip=True) if soup.find("title") else "")
        ).strip()

        # ---- Subtitle / description ----
        subtitulo = (
            json_ld.get("description")
            or self._meta(soup, "og:description")
            or self._meta(soup, "description")
        )
        if subtitulo:
            subtitulo = subtitulo.strip()

        # ---- Author ----
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
            # Fallback: common byline selectors for larepublica.pe
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

        # ---- Canonical URL ----
        url_canonica = (
            json_ld.get("url")
            or json_ld.get("mainEntityOfPage", {}).get("@id")
            or self._meta(soup, "og:url")
        )
        canon_tag = soup.find("link", rel="canonical")
        if not url_canonica and canon_tag:
            url_canonica = canon_tag.get("href")

        # ---- Image URL ----
        url_imagen = (
            json_ld.get("image", {}).get("url")
            if isinstance(json_ld.get("image"), dict)
            else json_ld.get("image")
        )
        if not url_imagen:
            url_imagen = self._meta(soup, "og:image")

        # ---- Publication & update dates ----
        fecha_publicacion = self._parse_date_flexible(
            json_ld.get("datePublished", "")
            or self._meta(soup, "article:published_time", "")
        )
        fecha_actualizacion = self._parse_date_flexible(
            json_ld.get("dateModified", "")
            or self._meta(soup, "article:modified_time", "")
        )
        # Fall back to common <time> elements
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

        # ---- Section from URL path ----
        path_parts = [p for p in urlparse(url).path.split("/") if p]
        seccion_fuente = path_parts[0] if path_parts else None

        # ---- Category from JSON-LD ----
        categoria_principal = None
        if "articleSection" in json_ld:
            raw = json_ld["articleSection"]
            categoria_principal = raw[0] if isinstance(raw, list) else raw

        # ---- Body text (for geo detection & hashing) ----
        content = self._extract_body(soup)

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

    def process_article(self, article_info: dict) -> Optional[tuple[NoticiaRecord, str]]:
        """Fetch, classify and build a NoticiaRecord for one article URL.

        Returns (NoticiaRecord, body_text) or None if irrelevant / failed.
        """
        url = article_info["url"]
        data = self.extract_article_content(url)

        if not data or not data.get("titulo"):
            return None

        scope, provincia, distrito, ubigeo = self.classify_geo(
            data["titulo"], data["content"]
        )

        if scope == "desconocido":
            return None  # Not Lima/Callao related

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
            categoria_principal=data["categoria_principal"],
            scope_geografico=scope,
            provincia=provincia,
            distrito=distrito,
            ubigeo=ubigeo,
            fecha_publicacion=data["fecha_publicacion"],
            fecha_actualizacion=data["fecha_actualizacion"],
            idioma="es",
            es_duplicado=False,
        )
        # hash_titulo is set in __post_init__; hash_contenido computed in noticia_to_dict
        return record, data["content"]

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

        results: list[tuple[NoticiaRecord, str]] = []

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
        "--workers", type=int, default=5, help="Concurrent worker threads"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON filename (auto-generated if omitted)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("La República News Scraper — Lima Metropolitana & Callao")
    print("=" * 60)

    scraper = LimaCallaoNewsScraper(
        start_date_str=args.start,
        end_date_str=args.end,
        max_workers=args.workers,
    )

    results = scraper.run()

    # ---- Build output payload ----
    articles_json = []
    for record, body in results:
        row = noticia_to_dict(record, contenido=body)
        # Attach a content preview (not stored in DB, but useful for review)
        row["_content_preview"] = body[:500] + "…" if len(body) > 500 else body
        articles_json.append(row)

    output = {
        "source": "La República",
        "slug_fuente": scraper.SLUG_FUENTE,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "date_range": {
            "start": scraper.start_date_str,
            "end": scraper.end_date_str,
        },
        "focus_areas": ["Lima Metropolitana", "Callao Province"],
        "total_articles_found": len(results),
        "articles": articles_json,
    }

    filename = args.output or f"lima_callao_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    # ---- Summary ----
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    print(f"Total articles found : {len(results)}")
    print(f"Results saved to     : {filename}")

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


if __name__ == "__main__":
    main()