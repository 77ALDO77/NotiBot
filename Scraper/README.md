# La República News Scraper - Lima Metropolitana & Callao

Este script extrae noticias de La República relacionadas con Lima Metropolitana y la Provincia del Callao desde enero 2026 hasta la fecha actual.

## Requisitos

- Python ≥3.14
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)
- Bibliotecas: bs4, requests

## Instalación

```bash
uv sync
```

## Uso

```bash
uv run python lima_callao_news_scraper.py
```

## Funcionalidades

1. **Descarga de sitemaps**: El script accede a los sitemaps XML de La República para obtener listas estructuradas de artículos
2. **Filtrado por fecha**: Procesa solo artículos desde el 1 de enero de 2026 hasta la fecha actual
3. **Detección de ubicación**: Identifica artículos relacionados con:
   - Lima Metropolitana (incluyendo todos sus distritos)
   - Provincia Constitucional del Callao
4. **Extracción de contenido**: Para cada artículo relevante, extrae:
   - Título
   - URL
   - Sección del sitio
   - Fecha de publicación
   - Vista previa del contenido (primeros 500 caracteres)
5. **Output JSON**: Guarda los resultados en un archivo JSON con timestamp

## Archivos generados

- `lima_callao_news_YYYYMMDD_HHMMSS.json`: Contiene todos los artículos encontrados
- El JSON incluye metadatos como fecha de scraping, rango de fechas y desglose por ubicación

## Notas importantes

- El script respeta las reglas del `robots.txt` evitando rutas restringidas
- Implementa delays entre peticiones para no sobrecargar el servidor
- Para uso intensivo o comercial, considere contactar a La República para obtener acceso oficial
- Los selectores pueden requerir ajustes si La República cambia su estructura HTML
- Algunos artículos pueden no tener contenido completo extraído debido a medidas anti-scraping del sitio

## Personalización

Para cambiar el rango de fechas, modifique la llamada en `main()`:
```python
articles = scrape_lima_callao_news("2026-01-01")  # Cambiar fecha de inicio
```

Para agregar más regiones de enfoque, edite la función `is_lima_callao_related()` y agregue las palabras clave correspondientes.