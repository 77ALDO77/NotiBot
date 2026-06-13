import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class ArcXpRssScraper:
    BASE_URL: str = ""
    SLUG_FUENTE: str = ""
    SOURCE_ID: int = 0
    SECTIONS: list[str] = []

    def __init__(self, session: requests.Session):
        self.session = session

    def get_feed_urls(self) -> list[str]:
        return [f"{self.BASE_URL}/arcio/rss/category/{s}/" for s in self.SECTIONS]

    def parse_feed(self, feed_url: str) -> list[dict]:
        try:
            resp = self.session.get(feed_url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            return []

        ns = {
            "content": "http://purl.org/rss/1.0/modules/content/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "media": "http://search.yahoo.com/mrss/",
        }

        articles = []
        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            pubdate_el = item.find("pubDate")
            creator_el = item.find("dc:creator", ns)
            desc_el = item.find("description")
            encoded_el = item.find("content:encoded", ns)
            media_el = item.find("media:content", ns)

            url = link_el.text.strip() if link_el is not None and link_el.text else None
            if not url:
                continue

            titulo = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not titulo:
                continue

            fecha = None
            if pubdate_el is not None and pubdate_el.text:
                try:
                    fecha = parsedate_to_datetime(pubdate_el.text.strip())
                except (ValueError, TypeError):
                    pass

            autor = None
            if creator_el is not None and creator_el.text:
                autor = creator_el.text.strip()

            subtitulo = None
            if desc_el is not None and desc_el.text:
                subtitulo = desc_el.text.strip()

            url_imagen = None
            if media_el is not None:
                url_imagen = media_el.get("url")

            contenido_html = None
            contenido_limpio = None
            if encoded_el is not None and encoded_el.text:
                contenido_html = encoded_el.text
                soup = BeautifulSoup(contenido_html, "html.parser")
                for skip in soup.select("script, style, div.publicidad, div[style*='#25D366']"):
                    skip.decompose()
                contenido_limpio = soup.get_text(separator=" ", strip=True)
                # Fallback image from encoded content
                if not url_imagen:
                    first_img = soup.find("img")
                    if first_img and first_img.get("src"):
                        url_imagen = first_img["src"]

            path_parts = [p for p in urlparse(url).path.split("/") if p]
            seccion_fuente = path_parts[0] if path_parts else None
            if seccion_fuente == "edicion" and len(path_parts) > 1:
                seccion_fuente = path_parts[1]

            categoria_principal = self._normalize_category(seccion_fuente, titulo=titulo)

            articles.append({
                "url": url,
                "url_canonica": url,
                "url_imagen": url_imagen,
                "titulo": titulo,
                "subtitulo": subtitulo,
                "autor": autor,
                "seccion_fuente": seccion_fuente,
                "categoria_principal": categoria_principal,
                "fecha_publicacion": fecha,
                "content": contenido_limpio or "",
                "contenido_html": contenido_html,
                "contenido_crudo": contenido_html,
            })

        return articles

    @staticmethod
    def _normalize_category(cat: str | None, titulo: str = "") -> str | None:
        from src.scraper.category_inference import infer_categoria
        return infer_categoria(cat, titulo)
