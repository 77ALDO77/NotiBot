"""Utilidades compartidas para los scripts EDA."""
import json
from pathlib import Path

import pandas as pd


def load_dataset(filename: str | None = None) -> dict:
    if filename:
        with open(filename, encoding="utf-8") as f:
            return json.load(f)

    json_files = list(Path(".").glob("*_news_*.json"))
    if not json_files:
        raise FileNotFoundError("No se encontraron archivos JSON de noticias en la carpeta eda/")

    latest = max(json_files, key=lambda p: p.stat().st_mtime)
    with open(latest, encoding="utf-8") as f:
        return json.load(f)


def load_dataframe(filename: str | None = None) -> tuple[pd.DataFrame, dict]:
    data_raw = load_dataset(filename)
    df = pd.DataFrame(data_raw.get("articles", []))
    return df, data_raw
