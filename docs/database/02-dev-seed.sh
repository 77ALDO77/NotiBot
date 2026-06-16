#!/bin/sh
# NotiBot — dev seed data (light dump)
# Decompresses and loads 02-dev-seed.sql.gz during first DB init

echo "NotiBot: loading dev seed data..."
gunzip -c /docker-entrypoint-initdb.d/02-dev-seed.sql.gz | psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "NotiBot: dev seed loaded successfully."
