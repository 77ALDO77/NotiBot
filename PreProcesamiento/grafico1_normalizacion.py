 
import json
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parent
EDA_DIR = ROOT.parent / "eda"


def load_noticias() -> list[dict]:
    local_file = ROOT / "noticias.json"
    if local_file.exists():
        with local_file.open(encoding="utf-8") as f:
            data = json.load(f)
    else:
        exports = sorted(EDA_DIR.glob("lima_callao_news_*.json"), reverse=True)
        if not exports:
            raise FileNotFoundError(
                "No se encontró noticias.json ni exportaciones en eda/lima_callao_news_*.json"
            )
        with exports[0].open(encoding="utf-8") as f:
            data = json.load(f)
        print(f"Usando datos de: {exports[0].name}")

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("articles"), list):
        return data["articles"]
    raise ValueError("Formato JSON no reconocido: se espera una lista o {'articles': [...]}")


# ── Función idéntica a la del proyecto (classifier.py) ─────────────────────
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
 
# ── Cargar datos reales ─────────────────────────────────────────────────────
noticias = load_noticias()
 
# Tomar 12 títulos que tengan tildes o caracteres especiales
titulos_raw = [n["titulo"] for n in noticias if n.get("titulo")]
muestra = [t for t in titulos_raw if any(c in t for c in "áéíóúüñÁÉÍÓÚÜÑ")][:12]
 
antes  = [t[:70] + "…" if len(t) > 70 else t for t in muestra]
despues = [normalize_text(t)[:70] + "…" if len(normalize_text(t)) > 70 else normalize_text(t)
           for t in muestra]
 
# ── Figura ──────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
fig.patch.set_facecolor("#F8F9FA")
 
y_pos = range(len(muestra))
COLOR_ANTES   = "#D94F3D"
COLOR_DESPUES = "#2E86AB"
 
for ax, textos, color, titulo_eje in [
    (axes[0], antes,   COLOR_ANTES,   "ANTES  (texto crudo del scraper)"),
    (axes[1], despues, COLOR_DESPUES, "DESPUÉS  (normalize_text aplicado)"),
]:
    ax.set_facecolor("#FFFFFF")
    ax.barh(list(y_pos), [1]*len(textos), color=color, alpha=0.08, height=0.85)
    for i, texto in enumerate(textos):
        ax.text(0.02, i, texto, va="center", ha="left",
                fontsize=9.2, color="#1A1A2E", fontfamily="monospace",
                wrap=True)
    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title(titulo_eje, fontsize=12, fontweight="bold",
                 color=color, pad=12)
    for spine in ax.spines.values():
        spine.set_visible(False)
 
# Línea divisoria
fig.add_artist(plt.Line2D([0.505, 0.505], [0.08, 0.95],
                           transform=fig.transFigure,
                           color="#CCCCCC", linewidth=1.5))
 
fig.suptitle("① Normalización de texto — NotiBot\n"
             "Minúsculas + eliminación de tildes (NFD) + regex con bordes \\b",
             fontsize=14, fontweight="bold", color="#1A1A2E", y=0.98)
 
# Fórmula en la parte inferior
fig.text(0.5, 0.01,
         'Fórmula:  NFD("piña colada")  →  filtrar Mn  →  "pina colada"     |     '
         'código: unicodedata.normalize("NFD", text)  +  category(c) != "Mn"',
         ha="center", fontsize=9, color="#555555", style="italic")
 
plt.tight_layout(rect=[0, 0.04, 1, 0.96])
output = ROOT / "grafico1_normalizacion.png"
plt.savefig(output, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Guardado: {output}")
plt.show()