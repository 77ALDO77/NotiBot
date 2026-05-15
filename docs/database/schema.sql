-- ============================================================
-- Schema: InteligenciaArtificial - PostgreSQL
-- Description: Esquema completo para la plataforma de noticias
-- ============================================================

CREATE SCHEMA IF NOT EXISTS "public";

-- ============================================================
-- Tablas base / de referencia
-- ============================================================

-- Fuentes de noticias (sitios web scrapeados)
CREATE TABLE "public"."fuentes" (
    "id" serial NOT NULL,
    "nombre" text NOT NULL UNIQUE,
    "slug" text NOT NULL UNIQUE,
    "url_base" text NOT NULL,
    "activa" boolean NOT NULL DEFAULT TRUE,
    "confiabilidad" double NOT NULL DEFAULT 1.0,
    "notas" text,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id")
);

-- Categorias tematicas
CREATE TABLE "public"."categorias" (
    "id" serial NOT NULL,
    "nombre" text NOT NULL UNIQUE,
    "slug" text NOT NULL UNIQUE,
    "descripcion" text,
    PRIMARY KEY ("id")
);

-- Tags / etiquetas
CREATE TABLE "public"."tags" (
    "id" bigserial NOT NULL,
    "nombre" text NOT NULL UNIQUE,
    "slug" text NOT NULL UNIQUE,
    PRIMARY KEY ("id")
);

-- Entidades nombradas (personas, lugares, organizaciones, etc.)
CREATE TABLE "public"."entidades" (
    "id" bigserial NOT NULL,
    "nombre" text NOT NULL,
    "nombre_normalizado" text NOT NULL,
    "tipo" text NOT NULL,
    "metadata" jsonb,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CHECK (tipo IN ('persona','lugar','organizacion','tema','evento','institucion'))
);
CREATE INDEX "entidades_idx_entidades_tipo_nombre" ON "public"."entidades" ("tipo", "nombre_normalizado");

-- Usuarios del sistema
CREATE TABLE "public"."usuarios" (
    "id" bigserial NOT NULL,
    "nombre_usuario" text NOT NULL UNIQUE,
    "correo" text NOT NULL UNIQUE,
    "hash_password" text,
    "estado" text NOT NULL DEFAULT 'activo',
    "preferencias" jsonb,
    "fecha_registro" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ultimo_acceso" timestamptz,
    PRIMARY KEY ("id"),
    CHECK (estado IN ('activo','suspendido','eliminado'))
);
CREATE INDEX "usuarios_idx_usuarios_estado" ON "public"."usuarios" ("estado");

-- ============================================================
-- Tablas principales
-- ============================================================

-- Noticias (articulo principal)
CREATE TABLE "public"."noticias" (
    "id" bigserial NOT NULL,
    "id_fuente" int,
    "url_original" text NOT NULL UNIQUE,
    "url_canonica" text,
    "url_imagen" text,
    "slug_fuente" text,
    "titulo" text NOT NULL,
    "subtitulo" text,
    "autor" text,
    "seccion_fuente" text,
    "categoria_principal" text,
    "scope_geografico" text NOT NULL DEFAULT 'desconocido',
    "provincia" text,
    "distrito" text,
    "ubigeo" text,
    "fecha_publicacion" timestamptz,
    "fecha_actualizacion" timestamptz,
    "hash_titulo" text,
    "hash_contenido" text,
    "idioma" text NOT NULL DEFAULT 'es',
    "es_duplicado" boolean NOT NULL DEFAULT FALSE,
    "id_noticia_canonica" bigint,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CHECK (scope_geografico IN ('lima_metropolitana','callao','desconocido'))
);
CREATE INDEX "noticias_idx_noticias_distrito" ON "public"."noticias" ("distrito");
CREATE INDEX "noticias_idx_noticias_fuente_fecha" ON "public"."noticias" ("id_fuente", "fecha_publicacion");
CREATE INDEX "noticias_idx_noticias_hash_contenido" ON "public"."noticias" ("hash_contenido");
CREATE INDEX "noticias_idx_noticias_scope_fecha" ON "public"."noticias" ("scope_geografico", "fecha_publicacion");

-- ============================================================
-- Tablas de contenido y analisis
-- ============================================================

-- Contenido extraido del scraping
CREATE TABLE "public"."noticias_contenido" (
    "id_noticia" bigint NOT NULL,
    "titulo_extraido" text,
    "bajada_extraida" text,
    "contenido_crudo" text,
    "contenido_limpio" text,
    "contenido_html" text,
    "raw_jsonld" jsonb,
    "raw_metadata" jsonb,
    "raw_response" jsonb,
    "longitud_caracteres" int,
    "longitud_palabras" int,
    "calidad_extraccion" text NOT NULL DEFAULT 'sin_validar',
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id_noticia"),
    CHECK (calidad_extraccion IN ('sin_validar','valida','parcial','fallida'))
);
CREATE INDEX "noticias_contenido_idx_noticias_contenido_raw_jsonld_gin" ON "public"."noticias_contenido" USING GIN ("raw_jsonld");
CREATE INDEX "noticias_contenido_idx_noticias_contenido_raw_metadata_gin" ON "public"."noticias_contenido" USING GIN ("raw_metadata");

-- Analisis de IA de las noticias
CREATE TABLE "public"."noticias_analisis" (
    "id_noticia" bigint NOT NULL,
    "resumen_ia" text,
    "resumen_corto_ia" text,
    "puntaje_sentimiento" double,
    "etiqueta_sentimiento" text,
    "relevancia_local" double,
    "score_confiabilidad" double,
    "score_calidad" double,
    "clasificacion_tematica" text,
    "clasificacion_modelo" text,
    "clasificacion_version" text,
    "estado_procesamiento" text NOT NULL DEFAULT 'pendiente',
    "estado_calidad" text NOT NULL DEFAULT 'sin_validar',
    "observaciones" text,
    "procesado_at" timestamptz,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id_noticia"),
    CHECK (puntaje_sentimiento >= -1 AND puntaje_sentimiento <= 1),
    CHECK (etiqueta_sentimiento IN ('negativo','neutral','positivo')),
    CHECK (estado_procesamiento IN (
        'pendiente','scrapeado','normalizado','procesado_llm','vectorizado','publicado','error','descartado'
    )),
    CHECK (estado_calidad IN (
        'sin_validar','valido','incompleto','ambiguo','duplicado','rechazado'
    ))
);
CREATE INDEX "noticias_analisis_idx_noticias_analisis_estado" ON "public"."noticias_analisis" ("estado_procesamiento", "estado_calidad");

-- Chunks de texto para RAG
CREATE TABLE "public"."noticias_chunks" (
    "id" bigserial NOT NULL,
    "id_noticia" bigint NOT NULL,
    "chunk_index" int NOT NULL,
    "texto_chunk" text NOT NULL,
    "tokens_estimados" int,
    "inicio_char" int,
    "fin_char" int,
    "metadata" jsonb,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id")
);
CREATE INDEX "noticias_chunks_idx_chunks_noticia" ON "public"."noticias_chunks" ("id_noticia", "chunk_index");

-- Busqueda full-text
CREATE TABLE "public"."noticias_busqueda" (
    "id_noticia" bigint NOT NULL,
    "documento_tsv" text NOT NULL,
    PRIMARY KEY ("id_noticia")
);
CREATE INDEX "noticias_busqueda_idx_noticias_busqueda_tsv" ON "public"."noticias_busqueda" USING GIN ("documento_tsv");

-- ============================================================
-- Tablas de relacion (M:N)
-- ============================================================

-- Noticias <-> Entidades
CREATE TABLE "public"."noticias_entidades" (
    "id_noticia" bigint NOT NULL,
    "id_entidad" bigint NOT NULL,
    "relevancia" double,
    "menciones" int,
    "origen_extraccion" text,
    PRIMARY KEY ("id_noticia", "id_entidad"),
    CHECK (origen_extraccion IN ('regex','ner','ia','manual'))
);
CREATE INDEX "noticias_entidades_idx_noticias_entidades_entidad" ON "public"."noticias_entidades" ("id_entidad");

-- Noticias <-> Categorias
CREATE TABLE "public"."noticias_categorias" (
    "id_noticia" bigint NOT NULL,
    "id_categoria" int NOT NULL,
    "peso" double,
    "origen" text,
    PRIMARY KEY ("id_noticia", "id_categoria"),
    CHECK (origen IN ('fuente','regla','ia'))
);
CREATE INDEX "noticias_categorias_idx_noticias_categorias_categoria" ON "public"."noticias_categorias" ("id_categoria");

-- Noticias <-> Tags
CREATE TABLE "public"."noticias_tags" (
    "id_noticia" bigint NOT NULL,
    "id_tag" bigint NOT NULL,
    PRIMARY KEY ("id_noticia", "id_tag")
);

-- ============================================================
-- Tablas de ingestion y pipeline
-- ============================================================

-- Seeds de fuentes para descubrimiento
CREATE TABLE "public"."fuentes_seeds" (
    "id" bigserial NOT NULL,
    "id_fuente" int NOT NULL,
    "tipo_seed" text NOT NULL,
    "url_seed" text NOT NULL,
    "scope_geografico" text NOT NULL,
    "activa" boolean NOT NULL DEFAULT TRUE,
    "prioridad" int NOT NULL DEFAULT 100,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CHECK (tipo_seed IN ('seccion','tag','busqueda','rss','sitemap')),
    CHECK (scope_geografico IN ('lima_metropolitana','callao','desconocido'))
);
CREATE INDEX "fuentes_seeds_idx_fuentes_seeds_fuente_activa" ON "public"."fuentes_seeds" ("id_fuente", "activa", "prioridad");

-- URLs descubiertas para scraping
CREATE TABLE "public"."ingesta_urls" (
    "id" bigserial NOT NULL,
    "id_fuente" int NOT NULL,
    "url_descubierta" text NOT NULL,
    "url_canonica" text,
    "scope_inferido" text NOT NULL DEFAULT 'desconocido',
    "origen_descubrimiento" text NOT NULL,
    "estado" text NOT NULL DEFAULT 'pendiente',
    "prioridad" int NOT NULL DEFAULT 100,
    "intentos" int NOT NULL DEFAULT 0,
    "ultimo_error" text,
    "discovered_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_attempt_at" timestamptz,
    "processed_at" timestamptz,
    PRIMARY KEY ("id"),
    CHECK (scope_inferido IN ('lima_metropolitana','callao','desconocido')),
    CHECK (origen_descubrimiento IN ('seed','crawler','manual','rss','sitemap')),
    CHECK (estado IN ('pendiente','procesando','procesado','descartado','error'))
);
CREATE INDEX "ingesta_urls_idx_ingesta_estado_prioridad" ON "public"."ingesta_urls" ("estado", "prioridad", "discovered_at");
CREATE INDEX "ingesta_urls_idx_ingesta_fuente_estado" ON "public"."ingesta_urls" ("id_fuente", "estado");

-- Pipeline de procesamiento
CREATE TABLE "public"."pipeline_jobs" (
    "id" bigserial NOT NULL,
    "job_type" text NOT NULL,
    "target_type" text NOT NULL,
    "target_id" bigint NOT NULL,
    "estado" text NOT NULL DEFAULT 'pendiente',
    "prioridad" int NOT NULL DEFAULT 100,
    "intentos" int NOT NULL DEFAULT 0,
    "max_intentos" int NOT NULL DEFAULT 3,
    "ultimo_error" text,
    "payload" jsonb,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "started_at" timestamptz,
    "finished_at" timestamptz,
    PRIMARY KEY ("id"),
    CHECK (job_type IN ('descubrimiento','scraping','normalizacion','clasificacion','resumen','vectorizacion')),
    CHECK (target_type IN ('fuente','ingesta_url','noticia','chunk')),
    CHECK (estado IN ('pendiente','ejecutando','completado','error','cancelado'))
);
CREATE INDEX "pipeline_jobs_idx_pipeline_jobs_estado_prioridad" ON "public"."pipeline_jobs" ("estado", "prioridad", "created_at");

-- Logs de scraping
CREATE TABLE "public"."scraping_logs" (
    "id" bigserial NOT NULL,
    "id_fuente" int,
    "id_noticia" bigint,
    "nivel" text NOT NULL,
    "mensaje" text NOT NULL,
    "metadata" jsonb,
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CHECK (nivel IN ('debug','info','warning','error'))
);
CREATE INDEX "scraping_logs_idx_scraping_logs_fuente_fecha" ON "public"."scraping_logs" ("id_fuente", "created_at");

-- ============================================================
-- Tablas de chat y RAG
-- ============================================================

-- Sesiones de chat
CREATE TABLE "public"."sesiones_chat" (
    "id" bigserial NOT NULL,
    "id_usuario" bigint NOT NULL,
    "titulo_sesion" text,
    "estado" text NOT NULL DEFAULT 'activa',
    "fecha_inicio" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "fecha_ultima_actividad" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CHECK (estado IN ('activa','cerrada','archivada'))
);
CREATE INDEX "sesiones_chat_idx_sesiones_usuario_actividad" ON "public"."sesiones_chat" ("id_usuario", "fecha_ultima_actividad");

-- Mensajes del chat
CREATE TABLE "public"."mensajes_chat" (
    "id" bigserial NOT NULL,
    "id_sesion" bigint NOT NULL,
    "rol" text NOT NULL,
    "contenido" text NOT NULL,
    "tokens_entrada" int,
    "tokens_salida" int,
    "modelo" text,
    "metadata" jsonb,
    "fecha" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CHECK (rol IN ('usuario','asistente','sistema'))
);
CREATE INDEX "mensajes_chat_idx_mensajes_sesion_fecha" ON "public"."mensajes_chat" ("id_sesion", "fecha");

-- Referencias RAG (relacion entre mensajes y chunks de noticias)
CREATE TABLE "public"."referencias_rag" (
    "id_mensaje" bigint NOT NULL,
    "id_noticia" bigint,
    "id_chunk" bigint,
    "score_relevancia" double,
    PRIMARY KEY ("id_mensaje", "id_noticia", "id_chunk")
);

-- ============================================================
-- Tablas de interaccion de usuario
-- ============================================================

-- Interacciones usuario-noticia
CREATE TABLE "public"."interacciones" (
    "id" bigserial NOT NULL,
    "id_usuario" bigint NOT NULL,
    "id_noticia" bigint NOT NULL,
    "tipo_interaccion" text NOT NULL,
    "valor" double,
    "metadata" jsonb,
    "fecha" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id"),
    CHECK (tipo_interaccion IN ('impresion','lectura','click','like','guardado','compartido','fake_flag'))
);
CREATE INDEX "interacciones_idx_interacciones_noticia_tipo" ON "public"."interacciones" ("id_noticia", "tipo_interaccion");
CREATE INDEX "interacciones_idx_interacciones_usuario_fecha" ON "public"."interacciones" ("id_usuario", "fecha");

-- Busquedas de usuarios
CREATE TABLE "public"."busquedas_usuario" (
    "id" bigserial NOT NULL,
    "id_usuario" bigint NOT NULL,
    "query_texto" text NOT NULL,
    "filtros" jsonb,
    "fecha" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id")
);
CREATE INDEX "busquedas_usuario_idx_busquedas_usuario_fecha" ON "public"."busquedas_usuario" ("id_usuario", "fecha");

-- Noticias guardadas por usuario
CREATE TABLE "public"."noticias_guardadas" (
    "id_usuario" bigint NOT NULL,
    "id_noticia" bigint NOT NULL,
    "fecha_guardado" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id_usuario", "id_noticia")
);

-- ============================================================
-- Foreign Keys
-- ============================================================

-- Noticias
ALTER TABLE "public"."noticias" ADD CONSTRAINT "fk_noticias_id_fuente_fuentes_id" FOREIGN KEY("id_fuente") REFERENCES "public"."fuentes"("id");
ALTER TABLE "public"."noticias" ADD CONSTRAINT "fk_noticias_id_noticia_canonica_noticias_id" FOREIGN KEY("id_noticia_canonica") REFERENCES "public"."noticias"("id");

-- Noticias Contenido
ALTER TABLE "public"."noticias_contenido" ADD CONSTRAINT "fk_noticias_contenido_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");

-- Noticias Analisis
ALTER TABLE "public"."noticias_analisis" ADD CONSTRAINT "fk_noticias_analisis_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");

-- Noticias Chunks
ALTER TABLE "public"."noticias_chunks" ADD CONSTRAINT "fk_noticias_chunks_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");

-- Noticias Busqueda
ALTER TABLE "public"."noticias_busqueda" ADD CONSTRAINT "fk_noticias_busqueda_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");

-- Noticias Entidades
ALTER TABLE "public"."noticias_entidades" ADD CONSTRAINT "fk_noticias_entidades_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");
ALTER TABLE "public"."noticias_entidades" ADD CONSTRAINT "fk_noticias_entidades_id_entidad_entidades_id" FOREIGN KEY("id_entidad") REFERENCES "public"."entidades"("id");

-- Noticias Categorias
ALTER TABLE "public"."noticias_categorias" ADD CONSTRAINT "fk_noticias_categorias_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");
ALTER TABLE "public"."noticias_categorias" ADD CONSTRAINT "fk_noticias_categorias_id_categoria_categorias_id" FOREIGN KEY("id_categoria") REFERENCES "public"."categorias"("id");

-- Noticias Tags
ALTER TABLE "public"."noticias_tags" ADD CONSTRAINT "fk_noticias_tags_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");
ALTER TABLE "public"."noticias_tags" ADD CONSTRAINT "fk_noticias_tags_id_tag_tags_id" FOREIGN KEY("id_tag") REFERENCES "public"."tags"("id");

-- Fuentes Seeds
ALTER TABLE "public"."fuentes_seeds" ADD CONSTRAINT "fk_fuentes_seeds_id_fuente_fuentes_id" FOREIGN KEY("id_fuente") REFERENCES "public"."fuentes"("id");

-- Ingesta URLs
ALTER TABLE "public"."ingesta_urls" ADD CONSTRAINT "fk_ingesta_urls_id_fuente_fuentes_id" FOREIGN KEY("id_fuente") REFERENCES "public"."fuentes"("id");

-- Scraping Logs
ALTER TABLE "public"."scraping_logs" ADD CONSTRAINT "fk_scraping_logs_id_fuente_fuentes_id" FOREIGN KEY("id_fuente") REFERENCES "public"."fuentes"("id");
ALTER TABLE "public"."scraping_logs" ADD CONSTRAINT "fk_scraping_logs_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");

-- Sesiones Chat
ALTER TABLE "public"."sesiones_chat" ADD CONSTRAINT "fk_sesiones_chat_id_usuario_usuarios_id" FOREIGN KEY("id_usuario") REFERENCES "public"."usuarios"("id");

-- Mensajes Chat
ALTER TABLE "public"."mensajes_chat" ADD CONSTRAINT "fk_mensajes_chat_id_sesion_sesiones_chat_id" FOREIGN KEY("id_sesion") REFERENCES "public"."sesiones_chat"("id");

-- Referencias RAG
ALTER TABLE "public"."referencias_rag" ADD CONSTRAINT "fk_referencias_rag_id_mensaje_mensajes_chat_id" FOREIGN KEY("id_mensaje") REFERENCES "public"."mensajes_chat"("id");
ALTER TABLE "public"."referencias_rag" ADD CONSTRAINT "fk_referencias_rag_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");
ALTER TABLE "public"."referencias_rag" ADD CONSTRAINT "fk_referencias_rag_id_chunk_noticias_chunks_id" FOREIGN KEY("id_chunk") REFERENCES "public"."noticias_chunks"("id");

-- Interacciones
ALTER TABLE "public"."interacciones" ADD CONSTRAINT "fk_interacciones_id_usuario_usuarios_id" FOREIGN KEY("id_usuario") REFERENCES "public"."usuarios"("id");
ALTER TABLE "public"."interacciones" ADD CONSTRAINT "fk_interacciones_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");

-- Busquedas Usuario
ALTER TABLE "public"."busquedas_usuario" ADD CONSTRAINT "fk_busquedas_usuario_id_usuario_usuarios_id" FOREIGN KEY("id_usuario") REFERENCES "public"."usuarios"("id");

-- Noticias Guardadas
ALTER TABLE "public"."noticias_guardadas" ADD CONSTRAINT "fk_noticias_guardadas_id_usuario_usuarios_id" FOREIGN KEY("id_usuario") REFERENCES "public"."usuarios"("id");
ALTER TABLE "public"."noticias_guardadas" ADD CONSTRAINT "fk_noticias_guardadas_id_noticia_noticias_id" FOREIGN KEY("id_noticia") REFERENCES "public"."noticias"("id");