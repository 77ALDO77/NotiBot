import json
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


P21_CATEGORY_MAP = {
    "politica": "Política",
    "elecciones": "Política",
    "lima": "Sociedad",
    "peru": "Nacional",
    "mundo": "Mundo",
    "economia": "Economía",
    "deportes": "Deportes",
    "espectaculos": "Espectáculos",
    "cultura": "Cultura",
    "tecnologia": "Tecnología",
    "opinion": "Opinión",
    "vida": "Sociedad",
    "salud": "Sociedad",
}


def _normalize_p21_category(cat: str | None) -> str | None:
    if not cat:
        return None
    key = cat.lower().strip()
    return P21_CATEGORY_MAP.get(key, cat.title())


class Peru21Scraper:
    SOURCE_ID = 3
    SLUG_FUENTE = "peru21"
    BASE_URL = "https://peru21.pe"
    SECTIONS = [
        "lima", "politica", "peru", "mundo", "economia",
        "deportes", "espectaculos", "cultura", "opinion",
        "tecnologia",
    ]

    def __init__(self, session: requests.Session):
        self.session = session

    def get_section_urls(self) -> list[str]:
        return [f"{self.BASE_URL}/{s}/" for s in self.SECTIONS]

    def parse_section_listing(self, section_url: str) -> list[dict]:
        try:
            resp = self.session.get(section_url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            return []

        soup = BeautifulSoup(resp.content, "html.parser")
        articles = []

        for node in soup.select("article.node--type-article.node--view-mode-teaser-liquido"):
            titulo_el = node.select_one(".titulo-teaser-liquido a")
            if not titulo_el or not titulo_el.get("href"):
                continue

            url = titulo_el["href"]
            if not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"

            titulo = titulo_el.get_text(strip=True)
            if not titulo:
                continue

            subtitulo_el = node.select_one(".entradilla-teaser-liquido p")
            subtitulo = subtitulo_el.get_text(strip=True) if subtitulo_el else None

            autor_el = node.select_one(".firma-teaser-liquido a")
            autor = autor_el.get_text(strip=True) if autor_el else None

            time_el = node.select_one(".fecha-teaser-liquido time")
            fecha = None
            if time_el and time_el.get("datetime"):
                fecha = self._parse_date(time_el["datetime"])

            seccion_el = node.select_one(".seccion-teaser-liquido a")
            seccion = seccion_el.get_text(strip=True) if seccion_el else None

            img_el = node.select_one("img")
            url_imagen = None
            if img_el:
                url_imagen = img_el.get("src") or img_el.get("data-src")

            articles.append({
                "url": url,
                "titulo": titulo,
                "subtitulo": subtitulo,
                "autor": autor,
                "fecha_publicacion": fecha,
                "seccion_fuente": seccion.lower() if seccion else None,
                "categoria_principal": _normalize_p21_category(seccion),
                "url_imagen": url_imagen,
            })

        return articles

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        date_str = date_str.strip()
        for fmt in (
            lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
            lambda s: datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc),
        ):
            try:
                return fmt(date_str)
            except (ValueError, TypeError):
                continue
        return None

    def extract_article(self, url: str) -> Optional[dict]:
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
        ).strip()

        subtitulo = (
            json_ld.get("description")
            or self._meta(soup, "og:description")
            or self._meta(soup, "description")
        )
        if subtitulo:
            subtitulo = subtitulo.strip()

        autor = None
        author_data = json_ld.get("author")
        if isinstance(author_data, dict):
            autor = author_data.get("name")
        elif isinstance(author_data, list) and author_data:
            autor = author_data[0].get("name") if isinstance(author_data[0], dict) else author_data[0]
        if not autor:
            autor_el = soup.select_one(".bl-firmas-full a[href^='/autor/']")
            if autor_el:
                autor = autor_el.get_text(strip=True)

        url_canonica = (
            json_ld.get("url")
            or self._meta(soup, "og:url")
        )
        canon_tag = soup.find("link", rel="canonical")
        if not url_canonica and canon_tag:
            url_canonica = canon_tag.get("href")

        url_imagen = None
        images = json_ld.get("image")
        if isinstance(images, dict) and images.get("url"):
            img_url = images["url"]
            if img_url and not img_url.startswith("http"):
                img_url = f"{self.BASE_URL}{img_url}"
            url_imagen = img_url
        if not url_imagen:
            url_imagen = self._meta(soup, "og:image")

        fecha_publicacion = self._parse_date(
            json_ld.get("datePublished", "")
        )
        if not fecha_publicacion:
            time_el = soup.select_one("time[datetime]")
            if time_el:
                fecha_publicacion = self._parse_date(time_el.get("datetime", ""))

        fecha_actualizacion = self._parse_date(
            json_ld.get("dateModified", "")
        )

        path_parts = [p for p in urlparse(url).path.split("/") if p]
        seccion_fuente = path_parts[0] if path_parts else None

        categoria_principal = (
            json_ld.get("articleSection")
            or self._meta(soup, "article:section")
        )
        if not categoria_principal:
            if seccion_fuente:
                categoria_principal = seccion_fuente

        keywords = json_ld.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        elif not keywords:
            kw_meta = self._meta(soup, "keywords", "")
            if kw_meta:
                keywords = [k.strip() for k in kw_meta.split(",")[:10] if k.strip()]
        if not keywords:
            tag_els = soup.select("meta[property='article:tag']")
            keywords = [t.get("content", "") for t in tag_els if t.get("content")]

        content = self._extract_body(soup, json_ld)
        content_html = self._extract_body_html(soup)

        return {
            "url": url,
            "url_canonica": url_canonica or url,
            "url_imagen": url_imagen,
            "titulo": titulo,
            "subtitulo": subtitulo,
            "autor": autor,
            "seccion_fuente": seccion_fuente,
            "categoria_principal": _normalize_p21_category(categoria_principal),
            "fecha_publicacion": fecha_publicacion,
            "fecha_actualizacion": fecha_actualizacion,
            "content": content,
            "contenido_html": content_html,
            "contenido_crudo": resp.text[:50000] if len(resp.text) > 100 else resp.text,
            "raw_jsonld": json_ld if json_ld else None,
            "raw_metadata": self._extract_all_meta(soup),
            "keywords": keywords,
        }

    @staticmethod
    def _extract_json_ld(soup: BeautifulSoup) -> dict:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, dict):
                    if data.get("@type") == "NewsArticle":
                        return data
                    if "@graph" in data:
                        for item in data["@graph"]:
                            if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                                return item
            except (json.JSONDecodeError, AttributeError):
                continue
        return {}

    @staticmethod
    def _meta(soup: BeautifulSoup, prop: str, default: str = "") -> str:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        return (tag.get("content", default) if tag else default) or default

    @staticmethod
    def _extract_body(soup: BeautifulSoup, json_ld: dict) -> str:
        body = json_ld.get("articleBody", "")
        if body and len(body) > 200:
            return body

        content_div = soup.select_one(".field--name-body")
        if content_div:
            for skip in content_div.select("div.publicidad-inline, div.publicidad-intext, "
                                            "div.embedded-entity, div.en-vivo, section"):
                skip.decompose()
            text = content_div.get_text(separator=" ", strip=True)
            if len(text) > 100:
                return text

        paragraphs = soup.select(".field--name-body p")
        if paragraphs:
            text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
            if len(text) > 100:
                return text

        return " ".join(
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 30
        )

    @staticmethod
    def _extract_body_html(soup: BeautifulSoup) -> Optional[str]:
        content_div = soup.select_one(".field--name-body")
        if content_div:
            for skip in content_div.select("div.publicidad-inline, div.publicidad-intext, "
                                            "div.embedded-entity, div.en-vivo, section"):
                skip.decompose()
            html = str(content_div)
            if len(html) > 100:
                return html
        paragraphs = soup.select(".field--name-body p")
        if paragraphs:
            return str(paragraphs[0].parent) if paragraphs[0].parent else None
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
