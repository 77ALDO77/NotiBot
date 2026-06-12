"""Utilidades compartidas para los scripts EDA."""
import json
from pathlib import Path

import pandas as pd

EDA_DIR = Path(__file__).resolve().parent


def load_dataset(filename: str | None = None) -> dict:
    if filename:
        path = Path(filename)
        if not path.is_absolute():
            path = EDA_DIR / path
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    json_files = list(EDA_DIR.glob("*_news_*.json"))
    if not json_files:
        raise FileNotFoundError(
            f"No se encontraron archivos JSON de noticias en {EDA_DIR}. "
            "Ejecuta primero: py -3.14 -m uv run python export_from_db.py"
        )

    latest = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"Usando dataset: {latest.name}")
    with open(latest, encoding="utf-8") as f:
        return json.load(f)


def load_dataframe(filename: str | None = None) -> tuple[pd.DataFrame, dict]:
    data_raw = load_dataset(filename)
    df = pd.DataFrame(data_raw.get("articles", []))
    return df, data_raw
