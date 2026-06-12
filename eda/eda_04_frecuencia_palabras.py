# EDA 04: FRECUENCIA DE PALABRAS
import re
from collections import Counter

import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from eda_common import load_dataframe
from eda_nlp import STOPWORDS, limpiar_texto

df, _data_raw = load_dataframe()

# Descargar recursos
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

def limpiar_texto(texto):
    """Limpia y normaliza texto"""
    if not isinstance(texto, str):
        return ""
    
    texto = texto.lower()
    texto = re.sub(r'http\S+|www\S+', '', texto)
    texto = re.sub(r'[^a-záéíóúñ\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def tokenizar_y_filtrar(texto):
    """Tokeniza y filtra stopwords"""
    if not texto:
        return []
    
    palabras = word_tokenize(texto)
    palabras = [p for p in palabras if p not in STOPWORDS and len(p) > 2]
    return palabras

def obtener_frecuencia_palabras(textos, top_n=50):
    """Obtiene palabras más frecuentes"""
    todas_palabras = []
    
    for texto in textos:
        texto_limpio = limpiar_texto(texto)
        palabras = tokenizar_y_filtrar(texto_limpio)
        todas_palabras.extend(palabras)
    
    frecuencia = Counter(todas_palabras)
    return frecuencia.most_common(top_n)

# ANÁLISIS DE FRECUENCIA
print("\n" + "="*70)
print("🔤 4. ANÁLISIS DE FRECUENCIA DE PALABRAS")
print("="*70)

# PALABRAS EN TÍTULOS
if 'titulo' in df.columns:
    print(f"\n📝 Palabras más frecuentes en TÍTULOS (Top 30):")
    frecuencia_titulo = obtener_frecuencia_palabras(df['titulo'].fillna(''), top_n=30)
    
    for i, (palabra, freq) in enumerate(frecuencia_titulo, 1):
        pct = 100 * freq / df['titulo'].notna().sum()
        barra = '▪' * int(freq / max([f for _, f in frecuencia_titulo]) * 40)
        print(f"  {i:2d}. {palabra:<15} {freq:>4} veces ({pct:>5.1f}%) {barra}")

# PALABRAS EN SUBTÍTULOS
if 'subtitulo' in df.columns:
    subtitulos_validos = df[df['subtitulo'].notna() & (df['subtitulo'].str.len() > 0)]['subtitulo']
    if len(subtitulos_validos) > 0:
        print(f"\n✍️  Palabras más frecuentes en SUBTÍTULOS (Top 30):")
        frecuencia_subtitulo = obtener_frecuencia_palabras(subtitulos_validos, top_n=30)
        
        for i, (palabra, freq) in enumerate(frecuencia_subtitulo, 1):
            pct = 100 * freq / len(subtitulos_validos)
            barra = '▪' * int(freq / max([f for _, f in frecuencia_subtitulo]) * 40)
            print(f"  {i:2d}. {palabra:<15} {freq:>4} veces ({pct:>5.1f}%) {barra}")

# PALABRAS COMBINADAS (TÍTULOS + SUBTÍTULOS)
if 'titulo' in df.columns:
    textos_combinados = (
        df['titulo'].fillna('') + ' ' + 
        df['subtitulo'].fillna('')
    )
    
    print(f"\n🌍 Palabras más frecuentes en TÍTULOS + SUBTÍTULOS (Top 50):")
    frecuencia_combinada = obtener_frecuencia_palabras(textos_combinados, top_n=50)
    
    for i, (palabra, freq) in enumerate(frecuencia_combinada, 1):
        pct = 100 * freq / len(df)
        barra = '▪' * int(freq / max([f for _, f in frecuencia_combinada]) * 30)
        print(f"  {i:2d}. {palabra:<15} {freq:>4} ({pct:>5.1f}%) {barra}")

# VISUALIZACIÓN DE FRECUENCIAS
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Top 20 palabras en títulos
if frecuencia_titulo:
    top_20_titulo = frecuencia_titulo[:20]
    palabras, freqs = zip(*top_20_titulo)
    colors = plt.cm.viridis(range(len(palabras)))
    axes[0, 0].barh(range(len(palabras)), freqs, color=colors)
    axes[0, 0].set_yticks(range(len(palabras)))
    axes[0, 0].set_yticklabels(palabras)
    axes[0, 0].set_title('Top 20 Palabras en Títulos', fontsize=12, fontweight='bold')
    axes[0, 0].set_xlabel('Frecuencia')
    axes[0, 0].invert_yaxis()

# Top 20 palabras en subtítulos
if 'subtitulo' in df.columns and len(subtitulos_validos) > 0:
    top_20_subtitulo = frecuencia_subtitulo[:20]
    palabras, freqs = zip(*top_20_subtitulo)
    colors = plt.cm.plasma(range(len(palabras)))
    axes[0, 1].barh(range(len(palabras)), freqs, color=colors)
    axes[0, 1].set_yticks(range(len(palabras)))
    axes[0, 1].set_yticklabels(palabras)
    axes[0, 1].set_title('Top 20 Palabras en Subtítulos', fontsize=12, fontweight='bold')
    axes[0, 1].set_xlabel('Frecuencia')
    axes[0, 1].invert_yaxis()

# Top 25 palabras combinadas
if frecuencia_combinada:
    top_25_combined = frecuencia_combinada[:25]
    palabras, freqs = zip(*top_25_combined)
    colors = plt.cm.cool(range(len(palabras)))
    axes[1, 0].barh(range(len(palabras)), freqs, color=colors)
    axes[1, 0].set_yticks(range(len(palabras)))
    axes[1, 0].set_yticklabels(palabras)
    axes[1, 0].set_title('Top 25 Palabras (Títulos + Subtítulos)', fontsize=12, fontweight='bold')
    axes[1, 0].set_xlabel('Frecuencia')
    axes[1, 0].invert_yaxis()

# Distribución de frecuencias (log scale)
if frecuencia_combinada:
    frecuencias_valores = [freq for _, freq in frecuencia_combinada]
    axes[1, 1].loglog(range(1, len(frecuencias_valores) + 1), sorted(frecuencias_valores, reverse=True), 'o-')
    axes[1, 1].set_title('Distribución de Frecuencias (Log-Log)', fontsize=12, fontweight='bold')
    axes[1, 1].set_xlabel('Rango de palabra')
    axes[1, 1].set_ylabel('Frecuencia')
    axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('eda_frecuencia_palabras.png', dpi=300, bbox_inches='tight')
plt.show()