#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------
# QuimioAnalytics - Apply PostgreSQL schema
# -----------------------------------------------------
# Este script aplica o arquivo database_schema_postgresql.sql
# usando cliente psql local.
# -----------------------------------------------------

DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-55432}"
DB_NAME="${DB_NAME:-quimioanalytics}"
SCHEMA_FILE="${SCHEMA_FILE:-database_schema_postgresql.sql}"

[[ -f "${SCHEMA_FILE}" ]] || {
  echo "[ERRO] Schema não encontrado: ${SCHEMA_FILE}"
  exit 1
}

command -v psql >/dev/null 2>&1 || {
  echo "[ERRO] psql não encontrado no PATH"
  exit 1
}

export PGPASSWORD="${DB_PASSWORD}"

echo "[INFO] Aplicando schema ${SCHEMA_FILE} em ${DB_HOST}:${DB_PORT}/${DB_NAME}..."
psql \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  -v ON_ERROR_STOP=1 \
  -f "${SCHEMA_FILE}"

echo "[OK] Schema aplicado com sucesso."
