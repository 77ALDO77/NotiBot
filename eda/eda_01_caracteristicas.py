# EDA 01: CARACTERÍSTICAS BÁSICAS DEL CONJUNTO DE DATOS
import json
import pandas as pd
from pathlib import Path

EDA_DIR = Path(__file__).resolve().parent

# Cargar datos
def load_dataset(filename=None):
    """Carga el archivo JSON más reciente"""
    if filename:
        path = Path(filename)
        if not path.is_absolute():
            path = EDA_DIR / path
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    json_files = list(EDA_DIR.glob('*_news_*.json'))
    if not json_files:
        raise FileNotFoundError(
            f"No se encontraron archivos JSON de noticias en {EDA_DIR}. "
            "Ejecuta primero: py -3.14 -m uv run python export_from_db.py"
        )
    
    latest = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"Usando dataset: {latest.name}")
    with open(latest, 'r', encoding='utf-8') as f:
        return json.load(f)

data_raw = load_dataset()
df = pd.DataFrame(data_raw.get('articles', []))

# CARACTERÍSTICAS BÁSICAS
print("="*70)
print("📊 1. CARACTERÍSTICAS BÁSICAS DEL CONJUNTO DE DATOS")
print("="*70)

print(f"\n📈 Estadísticas Generales:")
print(f"  • Total de artículos: {len(df):,}")
print(f"  • Fuente: {data_raw.get('source', 'N/A')}")
print(f"  • Fecha de scraping: {data_raw.get('scraped_at', 'N/A')}")
print(f"  • Rango de fechas: {data_raw.get('date_range', {}).get('start')} a {data_raw.get('date_range', {}).get('end')}")

# Información de duplicados
if 'es_duplicado' in df.columns:
    duplicados = df['es_duplicado'].sum()
    unicos = len(df) - duplicados
    print(f"\n🔄 Duplicados:")
    print(f"  • Artículos únicos: {unicos:,} ({100*unicos/len(df):.1f}%)")
    print(f"  • Duplicados: {duplicados:,} ({100*duplicados/len(df):.1f}%)")

# Columnas disponibles
print(f"\n📋 Columnas disponibles ({len(df.columns)}):")
for col in sorted(df.columns):
    null_count = df[col].isna().sum()
    null_pct = 100 * null_count / len(df)
    dtype = df[col].dtype
    print(f"  • {col:<25} ({dtype}) - {null_pct:.1f}% vacíos")

# Información de campos específicos
print(f"\n📊 Información de Campos Específicos:")
if 'seccion_normalizada' in df.columns:
    print(f"  • Secciones únicas: {df['seccion_normalizada'].nunique()}")
if 'distrito' in df.columns:
    print(f"  • Distritos únicos: {df[df['distrito'].notna()]['distrito'].nunique()}")
if 'provincia' in df.columns:
    print(f"  • Provincias únicas: {df[df['provincia'].notna()]['provincia'].nunique()}")
if 'autor' in df.columns:
    print(f"  • Autores únicos: {df[df['autor'].notna()]['autor'].nunique()}")