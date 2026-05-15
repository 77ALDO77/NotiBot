# Agentes OpenCode: Guia para este repositorio

## Estructura actual del repositorio
- **README.md**: Documenta la arquitectura planeada (Python backend FastAPI, Python IA, Next.js frontend)
- **Scraper/**: Proyecto Python existente usando uv (scrapping de noticias)

## Trabajando con el proyecto Scraper (Python)
Este es el unico componente implementado actualmente.

### Comandos esenciales
- **Entrypoint**: `cd Scraper && python main.py`
- **Instalar dependencias**: `cd Scraper && uv sync` (usa uv.lock y pyproject.toml)
- **Activar entorno virtual**: `source Scraper/.venv/bin/activate` (Linux/Mac) o `Scraper\.venv\Scripts\activate` (Windows)
- **Ejecutar directamente con uv**: `cd Scraper && uv run python main.py`

### Notas importantes
- El proyecto usa Python 3.14+ (ver pyproject.toml)
- Dependencias: bs4 (BeautifulSoup4) y requests
- Los archivos .json en Scraper/ son datos de scrapers anteriores (lima_callao_news_*.json)
- No hay tests configurados aun
- No hay configuracion de CI/CD

## Arquitectura futura
- **Backend**: Python con FastAPI (NO C#)
- **Frontend**: Next.js con bun
- **IA**: Python (NER, sentiment, classification, embeddings)
- **Infraestructura**: Docker y Kubernetes

## Que NO existe aun
- Directorio backend/ (Python FastAPI)
- Directorio frontend/ (Next.js)
- docker-compose.yml
- Manifiestos k8s/
- Scripts de build/test/lint

## Para desarrollo futuro
Cuando se implemente la arquitectura completa, verificar:
1. Existencia de directorios backend/ (Python FastAPI) y frontend/ (Next.js)
2. Archivos de configuracion como Dockerfile, docker-compose.yml, o manifiestos k8s/
3. Scripts de build/test/lint especificos para cada tecnologia