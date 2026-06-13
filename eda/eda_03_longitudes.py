# EDA 03: LONGITUDES
import matplotlib.pyplot as plt

from eda_common import load_dataframe

df, _data_raw = load_dataframe()

print("\n" + "="*70)
print("📏 3. ANÁLISIS DE LONGITUDES DE DOCUMENTOS")
print("="*70)

# TÍTULOS
if 'titulo' in df.columns:
    df['longitud_titulo'] = df['titulo'].fillna('').str.len()
    df['palabras_titulo'] = df['titulo'].fillna('').str.split().str.len()
    
    print(f"\n📖 TÍTULOS:")
    print(f"  • Longitud promedio: {df['longitud_titulo'].mean():.1f} caracteres")
    print(f"  • Longitud mínima: {df['longitud_titulo'].min():.0f} caracteres")
    print(f"  • Longitud máxima: {df['longitud_titulo'].max():.0f} caracteres")
    print(f"  • Desviación estándar: {df['longitud_titulo'].std():.1f}")
    print(f"  • Mediana: {df['longitud_titulo'].median():.1f} caracteres")
    print(f"  • Palabras promedio: {df['palabras_titulo'].mean():.1f}")
    print(f"  • Palabras mínimas: {df['palabras_titulo'].min():.0f}")
    print(f"  • Palabras máximas: {df['palabras_titulo'].max():.0f}")

# SUBTÍTULOS
if 'subtitulo' in df.columns:
    df['longitud_subtitulo'] = df['subtitulo'].fillna('').str.len()
    df['palabras_subtitulo'] = df['subtitulo'].fillna('').str.split().str.len()
    
    subtitulos_validos = df[df['longitud_subtitulo'] > 0]
    if len(subtitulos_validos) > 0:
        print(f"\n✍️  SUBTÍTULOS ({len(subtitulos_validos)} con contenido):")
        print(f"  • Longitud promedio: {subtitulos_validos['longitud_subtitulo'].mean():.1f} caracteres")
        print(f"  • Longitud mínima: {subtitulos_validos['longitud_subtitulo'].min():.0f} caracteres")
        print(f"  • Longitud máxima: {subtitulos_validos['longitud_subtitulo'].max():.0f} caracteres")
        print(f"  • Desviación estándar: {subtitulos_validos['longitud_subtitulo'].std():.1f}")
        print(f"  • Mediana: {subtitulos_validos['longitud_subtitulo'].median():.1f} caracteres")
        print(f"  • Palabras promedio: {subtitulos_validos['palabras_subtitulo'].mean():.1f}")
        print(f"  • Palabras mínimas: {subtitulos_validos['palabras_subtitulo'].min():.0f}")
        print(f"  • Palabras máximas: {subtitulos_validos['palabras_subtitulo'].max():.0f}")

# CONTENIDO PREVIEW
if '_content_preview' in df.columns:
    df['longitud_contenido'] = df['_content_preview'].fillna('').str.len()
    df['palabras_contenido'] = df['_content_preview'].fillna('').str.split().str.len()
    
    contenido_valido = df[df['longitud_contenido'] > 0]
    if len(contenido_valido) > 0:
        print(f"\n📄 CONTENIDO PREVIEW ({len(contenido_valido)} con contenido):")
        print(f"  • Longitud promedio: {contenido_valido['longitud_contenido'].mean():.1f} caracteres")
        print(f"  • Longitud mínima: {contenido_valido['longitud_contenido'].min():.0f} caracteres")
        print(f"  • Longitud máxima: {contenido_valido['longitud_contenido'].max():.0f} caracteres")
        print(f"  • Desviación estándar: {contenido_valido['longitud_contenido'].std():.1f}")
        print(f"  • Mediana: {contenido_valido['longitud_contenido'].median():.1f} caracteres")
        print(f"  • Palabras promedio: {contenido_valido['palabras_contenido'].mean():.1f}")

# VISUALIZACIONES DE LONGITUDES
fig, axes = plt.subplots(2, 3, figsize=(16, 10))

# Histograma de longitud de títulos
if 'longitud_titulo' in df.columns:
    axes[0, 0].hist(df['longitud_titulo'], bins=40, color='skyblue', edgecolor='black', alpha=0.7)
    axes[0, 0].axvline(df['longitud_titulo'].mean(), color='red', linestyle='--', 
                       linewidth=2, label=f"Media: {df['longitud_titulo'].mean():.1f}")
    axes[0, 0].set_title('Distribución de Longitud de Títulos', fontweight='bold')
    axes[0, 0].set_xlabel('Caracteres')
    axes[0, 0].set_ylabel('Frecuencia')
    axes[0, 0].legend()

# Histograma de longitud de subtítulos
if 'longitud_subtitulo' in df.columns:
    subtitulos_plot = df[df['longitud_subtitulo'] > 0]['longitud_subtitulo']
    if len(subtitulos_plot) > 0:
        axes[0, 1].hist(subtitulos_plot, bins=40, color='lightcoral', edgecolor='black', alpha=0.7)
        axes[0, 1].axvline(subtitulos_plot.mean(), color='red', linestyle='--', 
                          linewidth=2, label=f"Media: {subtitulos_plot.mean():.1f}")
        axes[0, 1].set_title('Distribución de Longitud de Subtítulos', fontweight='bold')
        axes[0, 1].set_xlabel('Caracteres')
        axes[0, 1].set_ylabel('Frecuencia')
        axes[0, 1].legend()

# Histograma de palabras por título
if 'palabras_titulo' in df.columns:
    axes[0, 2].hist(df['palabras_titulo'], bins=30, color='lightgreen', edgecolor='black', alpha=0.7)
    axes[0, 2].axvline(df['palabras_titulo'].mean(), color='red', linestyle='--', 
                      linewidth=2, label=f"Media: {df['palabras_titulo'].mean():.1f}")
    axes[0, 2].set_title('Palabras por Título', fontweight='bold')
    axes[0, 2].set_xlabel('Número de palabras')
    axes[0, 2].set_ylabel('Frecuencia')
    axes[0, 2].legend()

# Box plot de longitudes
if 'longitud_titulo' in df.columns:
    data_box = [
        df['longitud_titulo'],
        df[df['longitud_subtitulo'] > 0]['longitud_subtitulo'] if 'longitud_subtitulo' in df.columns else [],
        df[df['longitud_contenido'] > 0]['longitud_contenido'] if 'longitud_contenido' in df.columns else []
    ]
    data_box = [d for d in data_box if len(d) > 0]
    labels_box = ['Títulos', 'Subtítulos', 'Contenido'][:len(data_box)]
    axes[1, 0].boxplot(data_box, tick_labels=labels_box)
    axes[1, 0].set_title('Box Plot de Longitudes', fontweight='bold')
    axes[1, 0].set_ylabel('Caracteres')
    axes[1, 0].grid(axis='y', alpha=0.3)

# Scatter: Longitud vs Palabras (Títulos)
if 'longitud_titulo' in df.columns and 'palabras_titulo' in df.columns:
    axes[1, 1].scatter(df['palabras_titulo'], df['longitud_titulo'], alpha=0.5, s=30)
    axes[1, 1].set_title('Relación: Palabras vs Caracteres (Títulos)', fontweight='bold')
    axes[1, 1].set_xlabel('Número de palabras')
    axes[1, 1].set_ylabel('Caracteres')
    axes[1, 1].grid(True, alpha=0.3)

# Distribución de palabras por sección
if 'seccion_normalizada' in df.columns and 'palabras_titulo' in df.columns:
    top_secciones = df['seccion_normalizada'].value_counts().head(5).index
    datos_secciones = [df[df['seccion_normalizada'] == sec]['palabras_titulo'].values 
                       for sec in top_secciones]
    axes[1, 2].boxplot(datos_secciones, tick_labels=list(top_secciones))
    axes[1, 2].set_title('Palabras por Título - Top 5 Secciones', fontweight='bold')
    axes[1, 2].set_ylabel('Número de palabras')
    axes[1, 2].tick_params(axis='x', rotation=45)
    axes[1, 2].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('eda_longitudes.png', dpi=300, bbox_inches='tight')
plt.show()