# EDA 05: NUBES DE PALABRAS
import matplotlib.pyplot as plt
from wordcloud import WordCloud

from eda_common import load_dataframe
from eda_nlp import STOPWORDS, limpiar_texto

df, _data_raw = load_dataframe()

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

print("\n" + "="*70)
print("☁️  5. GENERANDO NUBES DE PALABRAS (WORDCLOUDS)")
print("="*70)

# WORDCLOUD DE TÍTULOS
if 'titulo' in df.columns:
    print("  • Generando wordcloud de títulos...")
    textos_titulo = ' '.join([limpiar_texto(t) for t in df['titulo'].fillna('') if isinstance(t, str)])
    
    if textos_titulo.strip():
        wc_titulo = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            colormap='viridis',
            stopwords=STOPWORDS,
            max_words=100
        ).generate(textos_titulo)
        
        axes[0, 0].imshow(wc_titulo, interpolation='bilinear')
        axes[0, 0].set_title('Wordcloud - Títulos', fontsize=14, fontweight='bold')
        axes[0, 0].axis('off')

# WORDCLOUD DE SUBTÍTULOS
if 'subtitulo' in df.columns:
    print("  • Generando wordcloud de subtítulos...")
    textos_subtitulo = ' '.join([
        limpiar_texto(t) for t in df['subtitulo'].fillna('') 
        if isinstance(t, str) and len(t) > 0
    ])
    
    if textos_subtitulo.strip():
        wc_subtitulo = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='plasma',
            stopwords=STOPWORDS,
            max_words=100
        ).generate(textos_subtitulo)
        
        axes[0, 1].imshow(wc_subtitulo, interpolation='bilinear')
        axes[0, 1].set_title('Wordcloud - Subtítulos', fontsize=14, fontweight='bold')
        axes[0, 1].axis('off')

# WORDCLOUD COMBINADA (TÍTULOS + SUBTÍTULOS)
if 'titulo' in df.columns:
    print("  • Generando wordcloud combinada...")
    textos_combinados = ' '.join([
        limpiar_texto(str(t) + ' ' + str(s))
        for t, s in zip(df['titulo'].fillna(''), df['subtitulo'].fillna(''))
    ])
    
    if textos_combinados.strip():
        wc_combinada = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='cool',
            stopwords=STOPWORDS,
            max_words=150
        ).generate(textos_combinados)
        
        axes[1, 0].imshow(wc_combinada, interpolation='bilinear')
        axes[1, 0].set_title('Wordcloud - Títulos + Subtítulos', fontsize=14, fontweight='bold')
        axes[1, 0].axis('off')

# WORDCLOUD POR SECCIÓN PRINCIPAL
if 'seccion_normalizada' in df.columns and 'titulo' in df.columns:
    print("  • Generando wordcloud por sección principal...")
    
    if df['seccion_normalizada'].notna().sum() > 0:
        seccion_principal = df['seccion_normalizada'].value_counts().index[0]
        textos_seccion = ' '.join([
            limpiar_texto(t)
            for t in df[df['seccion_normalizada'] == seccion_principal]['titulo'].fillna('')
            if isinstance(t, str)
        ])
        
        if textos_seccion.strip():
            wc_seccion = WordCloud(
                width=800,
                height=400,
                background_color='white',
                colormap='twilight',
                stopwords=STOPWORDS,
                max_words=100
            ).generate(textos_seccion)
            
            axes[1, 1].imshow(wc_seccion, interpolation='bilinear')
            axes[1, 1].set_title(f'Wordcloud - Sección: {seccion_principal}', fontsize=14, fontweight='bold')
            axes[1, 1].axis('off')

plt.tight_layout()
plt.savefig('wordclouds_eda.png', dpi=300, bbox_inches='tight')
print("\n✅ Wordclouds generadas correctamente")
plt.show()