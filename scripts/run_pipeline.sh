#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------
# QuimioAnalytics - Bootstrap + Run ETL
# -----------------------------------------------------
# O script:
# 1) valida Python
# 2) instala dependências
# 3) (opcional) aplica schema SQL no PostgreSQL
# 4) executa o pipeline Python
# -----------------------------------------------------

DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-quimioanalytics}"
DB_SCHEMA="${DB_SCHEMA:-quimioanalytics}"

APPLY_SCHEMA="${APPLY_SCHEMA:-1}"     # 1=aplica schema, 0=não aplica
INSTALL_DEPS="${INSTALL_DEPS:-1}"     # 1=instala deps, 0=não instala

IDENT_FILE="${IDENT_FILE:-data/identificacao.xlsx}"
ABUND_FILE="${ABUND_FILE:-data/abundancia.xlsx}"

export DB_USER DB_PASSWORD DB_HOST DB_PORT DB_NAME DB_SCHEMA

echo "[INFO] Configuração"
echo "  DB_HOST=${DB_HOST}"
echo "  DB_PORT=${DB_PORT}"
echo "  DB_NAME=${DB_NAME}"
echo "  DB_SCHEMA=${DB_SCHEMA}"

echo "[INFO] Validando Python..."
command -v python >/dev/null 2>&1 || { echo "[ERRO] python não encontrado"; exit 1; }

if [[ "${INSTALL_DEPS}" == "1" ]]; then
  echo "[INFO] Instalando dependências..."
  python -m pip install -r requirements.txt
fi

if [[ "${APPLY_SCHEMA}" == "1" ]]; then
  echo "[INFO] Aplicando schema PostgreSQL..."
  command -v psql >/dev/null 2>&1 || { echo "[ERRO] psql não encontrado"; exit 1; }

  export PGPASSWORD="${DB_PASSWORD}"
  psql \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -v ON_ERROR_STOP=1 \
    -f database_schema_postgresql.sql
fi

[[ -f "${IDENT_FILE}" ]] || { echo "[ERRO] Arquivo não encontrado: ${IDENT_FILE}"; exit 1; }
[[ -f "${ABUND_FILE}" ]] || { echo "[ERRO] Arquivo não encontrado: ${ABUND_FILE}"; exit 1; }

echo "[INFO] Executando pipeline..."
python main.py

echo "[OK] Pipeline concluído."
