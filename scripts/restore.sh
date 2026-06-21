#!/bin/bash
# ==============================================================================
# NotiBot — Script de Restauración de Base de Datos
# ==============================================================================
set -e

# Obtener directorio del script y raíz del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Validar argumentos
if [ -z "$1" ]; then
    echo "Uso: $0 <ruta_al_archivo_backup.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ Error: El archivo '$BACKUP_FILE' no existe."
    exit 1
fi

# Cargar variables de entorno
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Cargando variables desde $PROJECT_ROOT/.env"
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
    CLEAN_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg:\/\//postgresql:\/\//')
    if command -v python3 >/dev/null 2>&1; then
        DB_HOST=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.hostname or 'localhost')")
        DB_PORT=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.port or 5432)")
        DB_USER=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.username or 'notibot')")
        DB_PASSWORD=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.password or '')")
        DB_NAME=$(python3 -c "from urllib.parse import urlparse; p = urlparse('$CLEAN_URL'); print(p.path.lstrip('/'))")
    fi
fi

# Ajustar host si apunta al servicio interno de docker
if [ "$DB_HOST" = "postgres" ]; then
    DB_HOST="localhost"
fi

echo "=============================================================================="
echo "Iniciando proceso de Restauración para NotiBot..."
echo "Archivo: $BACKUP_FILE"
echo "Base de datos destino: $DB_NAME en $DB_HOST:$DB_PORT (Usuario: $DB_USER)"
echo "=============================================================================="

# Confirmar acción
read -p "ADVERTENCIA: Se borrarán todos los datos actuales de la base de datos. ¿Continuar? (s/N): " CONFIRM
if [ "$CONFIRM" != "s" ] && [ "$CONFIRM" != "S" ]; then
    echo "Operación cancelada."
    exit 0
fi

# Determinar método de ejecución
USE_DOCKER_EXEC=false
USE_DOCKER_RUN=false
USE_LOCAL=false

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q '^notibot-postgres$'; then
    USE_DOCKER_EXEC=true
    echo "✓ Contenedor 'notibot-postgres' detectado y en ejecución."
elif command -v psql >/dev/null 2>&1; then
    USE_LOCAL=true
    echo "✓ Herramienta 'psql' local detectada en el host."
elif command -v docker >/dev/null 2>&1; then
    USE_DOCKER_RUN=true
    echo "✓ Docker detectado. Se utilizará un contenedor temporal de postgres."
else
    echo "✗ Error: No se encontró 'psql' local ni Docker instalado."
    exit 1
fi

# 1. Limpiar el esquema público para evitar colisiones
echo "Wiping/Limpiando base de datos (DROP SCHEMA public CASCADE)..."
CLEAN_SQL="DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public; GRANT ALL ON SCHEMA public TO $DB_USER;"

if [ "$USE_DOCKER_EXEC" = true ]; then
    docker exec -i notibot-postgres psql -U "$DB_USER" -d "$DB_NAME" -c "$CLEAN_SQL"
elif [ "$USE_LOCAL" = true ]; then
    export PGPASSWORD="$DB_PASSWORD"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$CLEAN_SQL"
elif [ "$USE_DOCKER_RUN" = true ]; then
    local_net=""
    target_host="$DB_HOST"
    if [ "$DB_HOST" = "localhost" ] || [ "$DB_HOST" = "127.0.0.1" ]; then
        local_net="--net=host"
    fi
    docker run --rm $local_net -i -e PGPASSWORD="$DB_PASSWORD" postgres:16-alpine \
        psql -h "$target_host" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$CLEAN_SQL"
fi
echo "✓ Limpieza completada con éxito."

# 2. Restaurar datos
echo "Importando datos desde archivo de respaldo..."
if [ "$USE_DOCKER_EXEC" = true ]; then
    gunzip -c "$BACKUP_FILE" | docker exec -i notibot-postgres psql -U "$DB_USER" -d "$DB_NAME"
elif [ "$USE_LOCAL" = true ]; then
    export PGPASSWORD="$DB_PASSWORD"
    gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
elif [ "$USE_DOCKER_RUN" = true ]; then
    local_net=""
    target_host="$DB_HOST"
    if [ "$DB_HOST" = "localhost" ] || [ "$DB_HOST" = "127.0.0.1" ]; then
        local_net="--net=host"
    fi
    gunzip -c "$BACKUP_FILE" | docker run --rm $local_net -i -e PGPASSWORD="$DB_PASSWORD" postgres:16-alpine \
        psql -h "$target_host" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
fi

echo "=============================================================================="
echo "✓ ¡Restauración completada con éxito!"
echo "=============================================================================="
