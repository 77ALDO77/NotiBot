#!/bin/bash
# ==============================================================================
# NotiBot — Script de Copia de Seguridad (Backup)
# ==============================================================================
set -e

# Obtener directorio del script y raíz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Cargar variables de entorno
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Cargando variables desde $PROJECT_ROOT/.env"
    # Filtrar comentarios y líneas vacías antes de exportar
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^[[:space:]]*$' | xargs)
else
    echo "Advertencia: No se encontró el archivo .env en $PROJECT_ROOT"
fi

# Configuración por defecto
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-notibot}"
DB_PASSWORD="${POSTGRES_PASSWORD:-notibot_dev_2026}"
DB_NAME="${POSTGRES_DB:-notibot}"

# Si DATABASE_URL está definido, intentar extraer credenciales y host
if [ -n "$DATABASE_URL" ]; then
    # Remover prefijo asyncpg si existe
    CLEAN_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg:\/\//postgresql:\/\//')
    # Extraer componentes usando python de forma segura si está disponible
    if command -v python3 >/dev/null 2>&1; then
        DB_HOST=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.hostname or 'localhost')")
        DB_PORT=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.port or 5432)")
        DB_USER=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.username or 'notibot')")
        DB_PASSWORD=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.password or '')")
        DB_NAME=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.path.lstrip('/'))")
    fi
fi

# Ajustar host si se detecta que apunta al servicio 'postgres' de docker desde el host
if [ "$DB_HOST" = "postgres" ]; then
    DB_HOST="localhost"
fi

# Directorios de salida
BACKUP_DIR="$PROJECT_ROOT/backups"
SEED_FILE="$PROJECT_ROOT/docs/database/02-dev-seed.sql.gz"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FULL_BACKUP_FILE="$BACKUP_DIR/notibot_backup_$TIMESTAMP.sql.gz"

echo "=============================================================================="
echo "Iniciando proceso de Copia de Seguridad para NotiBot..."
echo "Base de datos: $DB_NAME en $DB_HOST:$DB_PORT (Usuario: $DB_USER)"
echo "=============================================================================="

# Determinar método de ejecución
USE_DOCKER_EXEC=false
USE_DOCKER_RUN=false
USE_LOCAL=false

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q '^notibot-postgres$'; then
    USE_DOCKER_EXEC=true
    echo "✓ Contenedor 'notibot-postgres' detectado y en ejecución."
elif command -v pg_dump >/dev/null 2>&1; then
    USE_LOCAL=true
    echo "✓ Herramienta 'pg_dump' local detectada en el host."
elif command -v docker >/dev/null 2>&1; then
    USE_DOCKER_RUN=true
    echo "✓ Docker detectado. Se utilizará un contenedor temporal de postgres."
else
    echo "✗ Error: No se encontró 'pg_dump' local ni Docker instalado."
    exit 1
fi

# Función para realizar el pg_dump
run_dump() {
    local dump_type="$1" # "full" o "data-only"
    local output_file="$2"
    
    local extra_args=""
    if [ "$dump_type" = "data-only" ]; then
        # Para el seed usamos --data-only --inserts
        extra_args="--data-only --inserts"
    fi
    
    if [ "$USE_DOCKER_EXEC" = true ]; then
        # Ejecutar pg_dump dentro del contenedor de postgres existente
        if [ "$dump_type" = "data-only" ]; then
            docker exec -i notibot-postgres pg_dump -U "$DB_USER" -d "$DB_NAME" $extra_args
        else
            docker exec -i notibot-postgres pg_dump -U "$DB_USER" -d "$DB_NAME"
        fi
    elif [ "$USE_LOCAL" = true ]; then
        # Ejecutar localmente
        export PGPASSWORD="$DB_PASSWORD"
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" $extra_args
    elif [ "$USE_DOCKER_RUN" = true ]; then
        # Ejecutar contenedor temporal
        # Si DB_HOST es localhost o 127.0.0.1, usar la red del host en docker
        local net_arg=""
        local target_host="$DB_HOST"
        if [ "$DB_HOST" = "localhost" ] || [ "$DB_HOST" = "127.0.0.1" ]; then
            net_arg="--net=host"
        fi
        docker run --rm $net_arg -i -e PGPASSWORD="$DB_PASSWORD" postgres:16-alpine \
            pg_dump -h "$target_host" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" $extra_args
    fi
}

# 1. Crear respaldo completo (Estructura + Datos)
echo "Generando copia de seguridad completa (esquema + datos)..."
run_dump "full" | gzip > "$FULL_BACKUP_FILE"
echo "✓ Copia completa guardada en: $FULL_BACKUP_FILE ($(du -sh "$FULL_BACKUP_FILE" | cut -f1))"

# 2. Crear/Actualizar semilla de desarrollo (Sólo Datos con ON CONFLICT DO NOTHING)
echo "Actualizando semilla de desarrollo (docs/database/02-dev-seed.sql.gz)..."
# Ejecutamos el volcado de datos, aplicamos sed para el ON CONFLICT DO NOTHING, y comprimimos
run_dump "data-only" \
    | sed -E '/^INSERT INTO/ s/\);$/) ON CONFLICT DO NOTHING;/g' \
    | gzip > "$SEED_FILE"

echo "✓ Semilla de desarrollo actualizada en: $SEED_FILE ($(du -sh "$SEED_FILE" | cut -f1))"
echo "=============================================================================="
echo "¡Copia de seguridad completada con éxito!"
echo "=============================================================================="
