"""Utilidades NLP compartidas para EDA."""
import re

import nltk
from nltk.corpus import stopwords

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

STOPWORDS = set(stopwords.words("spanish"))
STOPWORDS.update(
    {
        "noticias",
        "noticia",
        "lima",
        "callao",
        "perú",
        "peru",
        "comercio",
        "república",
        "republica",
        "día",
        "que",
        "del",
        "la",
        "de",
        "el",
        "y",
        "es",
        "en",
        "a",
        "se",
        "un",
        "una",
    }
)


def limpiar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        return ""

    texto = texto.lower()
    texto = re.sub(r"http\S+|www\S+", "", texto)
    texto = re.sub(r"[^a-záéíóúñ\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto
