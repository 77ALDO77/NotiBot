# Estructura del Proyecto InteligenciaArtificial

## Arquitectura General

```
InteligenciaArtificial/
├── backend/                    # Backend API en Python (FastAPI)
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/        # Endpoints API
│   │   │   └── deps/         # Dependencias inyectadas
│   │   ├── core/             # Configuracion central
│   │   ├── db/
│   │   │   ├── base.py      # Modelos base SQLAlchemy
│   │   │   └── session.py   # Sesion de bd
│   │   ├── models/           # Modelos de datos (SQLAlchemy)
│   │   ├── schemas/         # Esquemas Pydantic
│   │   ├── services/        # Logica de negocio
│   │   └── main.py
│   ├── alembic/             # Migraciones DB
│   ├── tests/
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   └── .env.example
│
├── ai/                         # Componentes de IA en Python
│   ├── models/                 # Modelos ML entrenados
│   ├── services/               # Servicios de IA
│   │   ├── ner/               # Named Entity Recognition
│   │   ├── sentiment/         # Analisis de sentimiento
│   │   ├── classification/   # Clasificacion de noticias
│   │   ├── summarization/     # Resumenes con LLM
│   │   └── embeddings/        # Generador de embeddings
│   ├── pipelines/              # Pipelines de procesamiento
│   ├── data/                  # Datos de entrenamiento
│   ├── main.py
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── uv.lock
│
├── frontend/                  # Frontend Next.js
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   │   ├── (routes)/    # Rutas de la aplicacion
│   │   │   └── api/         # API routes del cliente
│   │   ├── components/     # Componentes React
│   │   ├── lib/             # Utilidades
│   │   ├── hooks/           # Custom hooks
│   │   ├── stores/         # Estado global
│   │   └── styles/         # Estilos globales
│   ├── public/
│   ├── bun.lockb
│   ├── package.json
│   ├── next.config.js
│   ├── Dockerfile
│   └── tsconfig.json
│
├── k8s/                       # Manifiestos Kubernetes
│   ├── backend/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── ai/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── postgres/
│   │   ├── statefulset.yaml
│   │   └── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
│
├── docker-compose.yml        # Orquestacion local Docker
├── docker-compose.prod.yml   # Produccion
│
├── scripts/                   # Scripts de utilidad
│   ├── migrate_db.sh
│   ├── seed_data.sh
│   └── deploy.sh
│
├── docs/                      # Documentacion
│   ├── architecture.md
│   ├── api-reference.md
│   └── database/
│       └── schema.sql
│
├── tests/                     # Tests de integracion
├── AGENTS.md
├── README.md
└── LICENSE
```

## Diagrama de Entidad-Relacion (PostgreSQL)

```
+------------------------------------------------------------------+
|                              PUBLICO                               |
+--------------------------------------------------------------------+

+------------------+    +------------------+    +------------------+
|     FUENTES       |    |    CATEGORIAS    |    |      TAGS       |
+------------------+    +------------------+    +------------------+
| id (serial)       |    | id (serial)      |    | id (bigserial)  |
| nombre            |    | nombre           |    | nombre          |
| slug              |    | slug             |    | slug            |
| url_base          |    | descripcion      |    |                 |
| activa            |    +------------------+    +------------------+
| confiabilidad    |            ^                                  ^
| notas            |            |                                  |
| created_at       |            |                                  |
| updated_at       |            |                                  |
+--------+---------+            |                                  |
         |                   |                                     |
         |     +-------------+-------------+                       |
         |     |    NOTICIAS_CATEGORIAS    |                       |
         |     +---------------------------+                       |
         |     | id_noticia (FK)           |                       |
         |     | id_categoria (FK)         |                       |
         |     | peso (double)             |                       |
         |     | origen                    |                       |
         |     +---------------------------+                       |
         |     +---------------------------+                       |
         |     |       FUENTES_SEEDS       |                        | 
         |     +---------------------------+                       |
         |     | id (bigserial)            |                        |
         |     | id_fuente (FK)            |                        |
         |     | tipo_seed                 |                        |
         |     | url_seed                  |                   |
         |     | scope_geografico          |                   |
         |     | activa                    |                   |
         |     | prioridad                 |                   |
         |     | created_at                |                   |
         |     +---------------------------+                   |
         |     +---------------------------+                   |
         |     |       INGESTA_URLS      |                   |
         |     +---------------------------+                   |
         |     | id (bigserial)           |                   |
         |     | id_fuente (FK)           |                   |
         |     | url_descubierta         |                   |
         |     | url_canonica             |                   |
         |     | scope_inferido           |                   |
         |     | origen_descubrimiento   |                   |
         |     | estado                  |                   |
         |     | prioridad               |                   |
         |     | intentos                |                   |
         |     | ultimo_error            |                   |
         |     | discovered_at           |                   |
         |     | last_attempt_at          |                   |
         |     | processed_at            |                   |
         |     +---------------------------+                   |
         |     +---------------------------+                   |
         |     |         NOTICIAS          |<---------+        |
         |     +---------------------------+          |        |
         |     | id (bigserial)           |           |        |
         |     | id_fuente (FK)           |           |        |
         |     | url_original             |           |        |
         |     | url_canonica             |           |        |
         |     | url_imagen               |           |        |
         |     | slug_fuente              |           |        |
         |     | titulo                   |           |        |
         |     | subtitulo                |           |        |
         |     | autor                    |           |        |
         |     | seccion_fuente           |           |        |
         |     | categoria_principal      |           |        |
         |     | scope_geografico         |           |        |
         |     | provincia                |           |        |
         |     | distrito                 |           |        |
         |     | ubigeo                   |           |        |
         |     | fecha_publicacion        |           |        |
         |     | fecha_actualizacion      |           |        |
         |     | hash_titulo              |           |        |
         |     | hash_contenido           |           |        |
         |     | idioma                   |           |        |
         |     | es_duplicado             |           |        |
         |     | id_noticia_canonica      |           |        |
         |     | created_at               |           |        |
         |     | updated_at               |           |        |
         |     +-----------+--------------+           |        |
         |                 |                          |        |
         |     +-----------+--------------------------+--------+
         |     |                                               |
         |     | +-------------------------------------------+ |
         |     | |         NOTICIAS_CONTENIDO              | |
         |     | +-------------------------------------------+ |
         |     | | id_noticia (FK)                        | |
         |     | | titulo_extraido                         | |
         |     | | bajada_extraida                         | |
         |     | | contenido_crudo                        | |
         |     | | contenido_limpio                      | |
         |     | | contenido_html                        | |
         |     | | raw_jsonld (jsonb)                   | |
         |     | | raw_metadata (jsonb)                  | |
         |     | | raw_response (jsonb)                  | |
         |     | | longitud_caracteres                    | |
         |     | | longitud_palabras                     | |
         |     | | calidad_extraccion                    | |
         |     | | created_at                           | |
         |     | | updated_at                           | |
         |     | +-------------------------------------------+ |
         |     | +-------------------------------------------+ |
         |     | |         NOTICIAS_ANALISIS             | |
         |     | +-------------------------------------------+ |
         |     | | id_noticia (FK)                        | |
         |     | | resumen_ia                             | |
         |     | | resumen_corto_ia                      | |
         |     | | puntaje_sentimiento                   | |
         |     | | etiqueta_sentimiento                 | |
         |     | | relevancia_local                    | |
         |     | | score_confiabilidad                 | |
         |     | | score_calidad                        | |
         |     | | clasificacion_tematica               | |
         |     | | clasificacion_modelo               | |
         |     | | clasificacion_version               | |
         |     | | estado_procesamiento                | |
         |     | | estado_calidad                     | |
         |     | | observaciones                       | |
         |     | | procesado_at                        | |
         |     | | created_at                          | |
         |     | | updated_at                          | |
         |     | +-------------------------------------------+ |
         |     | +-------------------------------------------+ |
         |     | |         NOTICIAS_CHUNKS              | |
         |     | +-------------------------------------------+ |
         |     | | id (bigserial)                        | |
         |     | | id_noticia (FK)                        | |
         |     | | chunk_index                          | |
         |     | | texto_chunk                         | |
         |     | | tokens_estimados                    | |
         |     | | inicio_char                        | |
         |     | | fin_char                           | |
         |     | | metadata (jsonb)                  | |
         |     | | created_at                         | |
         |     | +-------------------------------------------+ |
         |     | +-------------------------------------------+ |
         |     | |       NOTICIAS_ENTIDADES              | |
         |     | +-------------------------------------------+ |
         |     | | id_noticia (FK)                        | |
         |     | | id_entidad (FK)                    | |
         |     | | relevancia                          | |
         |     | | menciones                           | |
         |     | | origen_extraccion                  | |
         |     | +-------------------------------------------+ |
         |     | +-------------------------------------------+ |
         |     | |        NOTICIAS_BUSQUEDA              | |
         |     | +-------------------------------------------+ |
         |     | | id_noticia (FK)                        | |
         |     | | documento_tsv                       | |
         |     | +-------------------------------------------+ |
         |     | +-------------------------------------------+ |
         |     | |       NOTICIAS_CATEGORIAS            | |
         |     | +-------------------------------------------+ |
         |     | | id_noticia (FK)                        | |
         |     | | id_categoria (FK)                 | |
         |     | | peso                                | |
         |     | | origen                              | |
         |     | +-------------------------------------------+ |
         |     | +-------------------------------------------+ |
         |     | |          NOTICIAS_TAGS                 | |
         |     | +-------------------------------------------+ |
         |     | | id_noticia (FK)                        | |
         |     | | id_tag (FK)                      | |
         |     | +-------------------------------------------+ |
         |     | +-------------------------------------------+ |
         |     | |         SCRAPING_LOGS                | |
         |     | +-------------------------------------------+ |
         |     | | id (bigserial)                        | |
         |     | | id_fuente (FK)                        | |
         |     | | id_noticia (FK)                        | |
         |     | | nivel                               | |
         |     | | mensaje                             | |
         |     | | metadata (jsonb)                    | |
         |     | | created_at                          | |
         |     | +-------------------------------------------+ |
         |     +-----------------------------------------------+
         |                                                    |
         +--------------------------------------------+          |
         |         PIPELINE_JOBS                      |          |
         +-------------------------------------------+          |
         | id (bigserial)                            |          |
         | job_type                                 |          |
         | target_type                             |          |
         | target_id                               |          |
         | estado                                  |          |
         | prioridad                               |          |
         | intentos                                |          |
         | max_intentos                            |          |
         | ultimo_error                            |          |
         | payload (jsonb)                         |          |
         | created_at                              |          |
         | started_at                              |          |
         | finished_at                             |          |
         +-------------------------------------------+          |
         +-------------------------------------------+          |
         |            ENTIDADES                      |          |
         +-------------------------------------------+          |
         | id (bigserial)                            |          |
         | nombre                                  |          |
         | nombre_normalizado                     |          |
         | tipo                                   |          |
         | metadata (jsonb)                       |          |
         | created_at                             |          |
         +-------------------------------------------+          |
         +-------------------------------------------+          |
         |             USUARIOS                     |          |
         +-------------------------------------------+          |
         | id (bigserial)                            |          |
         | nombre_usuario                         |          |
         | correo                                 |          |
         | hash_password                          |          |
         | estado                                 |          |
         | preferencias (jsonb)                   |          |
         | fecha_registro                          |          |
         | ultimo_acceso                          |          |
         +-------------------+---------------------+          |
                           |                                       |
         +---------------+-+------------------------------------+
         |              SESIONES_CHAT                      |
         +-------------------------------------------+         |
         | id (bigserial)                            |         |
         | id_usuario (FK)                         |         |
         | titulo_sesion                          |         |
         | estado                               |         |
         | fecha_inicio                          |         |
         | fecha_ultima_actividad                |         |
         +-------------------+---------------------+         |
                           |                                      |
         +---------------+-+-------------------------+
         |             MENSAJES_CHAT                 |
         +-------------------------------------------+         |
         | id (bigserial)                            |         |
         | id_sesion (FK)                            |         |
         | rol                                       |         |
         | contenido                                 |         |
         | tokens_entrada                            |         |
         | tokens_salida                             |         |
         | modelo                                    |         |
         | metadata (jsonb)                          |         |
         | fecha                                     |         |
         +-------------------+-----------------------+         |
                           |                                      |
         +---------------+-+------------------------------------+
         |            REFERENCIAS_RAG                  |
         +-------------------------------------------+         |
         | id_mensaje (FK)                         |         |
         | id_noticia (FK)                        |         |
         | id_chunk (FK)                          |         |
         | score_relevancia                       |         |
         +-------------------------------------------+         |
         +-------------------------------------------+         |
         |            INTERACCIONES                     |         |
         +-------------------------------------------+         |
         | id (bigserial)                            |         |
         | id_usuario (FK)                         |         |
         | id_noticia (FK)                        |         |
         | tipo_interaccion                       |         |
         | valor                                |         |
         | metadata (jsonb)                       |         |
         | fecha                                |         |
         +-------------------------------------------+         |
         +-------------------------------------------+         |
         |          BUSQUEDAS_USUARIO                 |         |
         +-------------------------------------------+         |
         | id (bigserial)                            |         |
         | id_usuario (FK)                         |         |
         | query_texto                          |         |
         | filtros (jsonb)                       |         |
         | fecha                                |         |
         +-------------------------------------------+         |
         +-------------------------------------------+         |
         |        NOTICIAS_GUARDADAS                |         |
         +-------------------------------------------+         |
         | id_usuario (FK)                         |         |
         | id_noticia (FK)                        |         |
         | fecha_guardado                         |         |
         +-------------------------------------------+         |
         +-------------------------------------------+

+------------------------------------------------------------------+
```

## Flujo de Procesamiento

```
FUENTES → FUENTES_SEEDS → INGESTA_URLS → NOTICIAS
                                         │
                                         ▼
                         +------------------------------+
                         |     PIPELINE JOBS            |
                         | descubrimiento → scraping →  |
                         | normalizacion → clasif.      |
                         | resumen → vectorizacion      |
                         +------------------------------+
                                         │
                                         ▼
              NOTICIAS_CHUNKS ──→ ENTIDADES ──→ NOTICIAS_ENTIDADES
              NOTICIAS_ANALISIS
              NOTICIAS_BUSQUEDA (Full-Text Search)
```

## Conexiones entre Servicios

```
+-------------------+
|   FRONTEND        |  Puerto: 3000
|   (Next.js)       |
+--------+----------+
         │ REST API
         ▼
+-------------------+
|   BACKEND API     |  Puerto: 8000
|   (FastAPI)       |
|   - /api/*        |
|   - /ws/*         |
+--------+----------+
         │
         ▼
+-------------------+
|   SERVICIOS IA    |  Puertos: 8001-8005
|   (Python)        |
|   NER             |  8001
|   Sentiment       |  8002
|   Classification  |  8003
|   Summarization   |  8004
|   Embeddings      |  8005
+--------+----------+
         │
         ▼
+-------------------+
|   POSTGRESQL     |  Puerto: 5432
+-------------------+
```