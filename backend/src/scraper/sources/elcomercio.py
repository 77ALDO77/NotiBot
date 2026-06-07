import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


EC_CATEGORY_MAP = {
    "elecciones": "Política",
    "congreso": "Política",
    "sucesos": "Sociedad",
    "policiales": "Sociedad",
    "accidentes": "Sociedad",
    "transporte": "Sociedad",
    "obras": "Sociedad",
    "justicia": "Sociedad",
    "actualidad": "Sociedad",
    "columnistas": "Opinión",
    "cultural": "Cultura",
    "música": "Espectáculos",
    "ecdata": "Datos",
    "archivo el comercio": "Historia",
    "piura": "Nacional",
    "perú": "Nacional",
    "cine y series": "Espectáculos",
    "mundo": "Mundo",
    "economía": "Economía",
    "deporte total": "Deportes",
    "deportes": "Deportes",
}


def _normalize_ec_category(cat: str | None, titulo: str = "") -> str | None:
    from src.scraper.category_inference import infer_categoria
    return infer_categoria(cat)


class ElComercioScraper:
    SOURCE_ID = 2
    SLUG_FUENTE = "elcomercio"

    def __init__(self, session: requests.Session):
        self.session = session

    def get_sitemap_index_urls(self) -> list[str]:
        sections = [
            "lima", "politica", "peru", "mundo", "economia", "deporte-total",
            "tecnologia", "luces", "opinion",
        ]
        return [
            f"https://elcomercio.pe/sitemap/news/{s}/?outputType=xml"
            for s in sections
        ]

    def parse_sitemap(self, sitemap_url: str) -> list[dict]:
        try:
            resp = self.session.get(sitemap_url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
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
                if loc_elem is None or not loc_elem.text:
                    continue
                url = loc_elem.text.strip()

                lastmod_elem = url_elem.find("lastmod", ns)
                lastmod = None
                if lastmod_elem is not None and lastmod_elem.text:
                    lastmod = self._parse_date(lastmod_elem.text)

                urls.append({"url": url, "lastmod": lastmod})

            return urls
        except ET.ParseError:
            return []

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
            autor_el = soup.select_one("div.sc__author-nd a.sc__author-nd-a")
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
        if isinstance(images, list) and images:
            url_imagen = images[0].get("url")
        if not url_imagen:
            img_el = soup.select_one("img.lazy.sc__image.w-full")
            if img_el:
                url_imagen = img_el.get("data-src") or img_el.get("src")
        if not url_imagen:
            url_imagen = self._meta(soup, "og:image")

        fecha_publicacion = self._parse_date(
            json_ld.get("datePublished", "")
            or self._meta(soup, "article:published_time", "")
        )
        fecha_actualizacion = self._parse_date(
            json_ld.get("dateModified", "")
            or self._meta(soup, "article:modified_time", "")
        )

        path_parts = [p for p in urlparse(url).path.split("/") if p]
        seccion_fuente = path_parts[0] if path_parts else None

        categoria_principal = None
        article_section = json_ld.get("articleSection") or self._meta(soup, "article:section")
        if article_section:
            categoria_principal = article_section

        if not categoria_principal:
            breadcrumbs = soup.select("div.breadcrumblist a.breadcrumblist_link div")
            if breadcrumbs:
                categoria_principal = breadcrumbs[-1].get_text(strip=True)

        keywords = json_ld.get("keywords", [])
        if not keywords:
            kw_meta = self._meta(soup, "keywords", "")
            if kw_meta:
                keywords = [k.strip() for k in kw_meta.split(",")[:10] if k.strip()]

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
            "categoria_principal": _normalize_ec_category(categoria_principal, titulo),
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
                    if data.get("@type") == "ReportageNewsArticle":
                        return data
                    if "@graph" in data:
                        for item in data["@graph"]:
                            if isinstance(item, dict) and item.get("@type") == "ReportageNewsArticle":
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

        paragraphs = soup.select("p.sc__font-paragraph")
        if paragraphs:
            text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
            if len(text) > 150:
                return text

        content_div = soup.select_one("div.sc__content")
        if content_div:
            text = content_div.get_text(separator=" ", strip=True)
            if len(text) > 150:
                return text

        return " ".join(
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 30
        )

    @staticmethod
    def _extract_body_html(soup: BeautifulSoup) -> Optional[str]:
        content_div = soup.select_one("div.sc__content")
        if content_div:
            html = str(content_div)
            if len(html) > 100:
                return html
        paragraphs = soup.select("p.sc__font-paragraph")
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
