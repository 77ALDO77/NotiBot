# EDA 02: DISTRIBUCIONES
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

from eda_common import load_dataframe

df, _data_raw = load_dataframe()

# Configurar estilo
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (18, 14)
plt.rcParams['font.size'] = 10

fig = plt.figure(figsize=(18, 14))

# 1. DISTRIBUCIÓN POR SECCIONES
print("\n" + "="*70)
print("📍 2. DISTRIBUCIONES: SECCIONES, DISTRITOS Y GEOGRAFÍA")
print("="*70)

if 'seccion_normalizada' in df.columns:
    print("\n📰 Distribución por Sección:")
    secciones = df['seccion_normalizada'].value_counts()
    
    # Gráfico
    ax1 = plt.subplot(3, 3, 1)
    colors = plt.cm.Set3(range(len(secciones)))
    secciones.plot(kind='barh', ax=ax1, color=colors)
    ax1.set_title('Distribución por Sección', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Cantidad de artículos')
    
    # Impresión en consola
    for sec, count in secciones.items():
        pct = 100 * count / len(df)
        barra = '█' * int(pct / 2)
        print(f"  {sec:<20} {count:>5} ({pct:>5.1f}%) {barra}")

# 2. DISTRIBUCIÓN POR DISTRITOS (TOP 15)
if 'distrito' in df.columns:
    print(f"\n🏘️  Distribución por Distrito (Top 15):")
    distritos_válidos = df[df['distrito'].notna()]['distrito'].value_counts()
    
    # Gráfico
    ax2 = plt.subplot(3, 3, 2)
    distritos_top15 = distritos_válidos.head(15)
    colors = plt.cm.Spectral(range(len(distritos_top15)))
    distritos_top15.plot(kind='barh', ax=ax2, color=colors)
    ax2.set_title('Top 15 Distritos', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Cantidad de artículos')
    
    # Impresión en consola
    for dist, count in distritos_top15.items():
        pct = 100 * count / len(df)
        barra = '█' * int(pct / 2)
        print(f"  {dist:<25} {count:>5} ({pct:>5.1f}%) {barra}")
    
    sin_dist = df['distrito'].isna().sum()
    print(f"  {'Sin clasificar':<25} {sin_dist:>5} ({100*sin_dist/len(df):>5.1f}%)")

# 3. DUPLICADOS VS ÚNICOS
if 'es_duplicado' in df.columns:
    print(f"\n🔄 Artículos Únicos vs Duplicados:")
    ax3 = plt.subplot(3, 3, 3)
    duplicados_count = df['es_duplicado'].value_counts()
    labels = ['Únicos', 'Duplicados']
    sizes = [duplicados_count.get(False, 0), duplicados_count.get(True, 0)]
    colors_pie = ['#2ecc71', '#e74c3c']
    wedges, texts, autotexts = ax3.pie(sizes, labels=labels, autopct='%1.1f%%',
                                         colors=colors_pie, startangle=90)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    ax3.set_title('Artículos Únicos vs Duplicados', fontsize=12, fontweight='bold')
    
    for label, size in zip(labels, sizes):
        print(f"  {label}: {size} ({100*size/len(df):.1f}%)")

# 4. PROVINCIAS
if 'provincia' in df.columns and df['provincia'].notna().sum() > 0:
    print(f"\n🌐 Distribución por Provincia:")
    provincias = df['provincia'].value_counts()
    for prov, count in provincias.items():
        pct = 100 * count / len(df)
        print(f"  {prov:<20} {count:>5} ({pct:>5.1f}%)")

plt.tight_layout()
plt.savefig('eda_distribuciones.png', dpi=300, bbox_inches='tight')
plt.show()