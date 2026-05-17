#!/bin/sh
set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-notibot}"; do
  sleep 2
done

echo "PostgreSQL is ready. Running schema..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  -h "${POSTGRES_HOST:-postgres}" \
  -p "${POSTGRES_PORT:-5432}" \
  -U "${POSTGRES_USER:-notibot}" \
  -d "${POSTGRES_DB:-notibot}" \
  -f /docker-entrypoint-initdb.d/01-schema.sql

echo "Schema applied successfully."
