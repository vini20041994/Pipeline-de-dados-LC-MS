#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------
# QuimioAnalytics - Script geral de execução (SQL + ETL)
# -----------------------------------------------------
# Este script centraliza TODO o fluxo operacional do projeto.
#
# Etapas executadas (comportamento padrão):
# 1) sobe os containers SQL (PostgreSQL + Adminer) via Docker Compose;
# 2) valida o interpretador Python do host;
# 3) instala dependências Python no ambiente do host (opcional);
# 4) aplica o schema SQL no PostgreSQL (opcional);
# 5) valida arquivos de entrada do ETL;
# 6) executa o pipeline Python (main.py).
#
# Objetivo: manter apenas um ponto de entrada para setup + execução.
#
# Dependências/ferramentas utilizadas pelo script:
# - docker compose: para subir PostgreSQL e Adminer (quando START_DOCKER=1)
# - python/python3: execução da aplicação
# - pip (via python -m pip): instalação de dependências do requirements.txt
# - psql: para aplicação do schema SQL (quando APPLY_SCHEMA=1)
# -----------------------------------------------------

DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-55432}"
DB_NAME="${DB_NAME:-quimioanalytics}"
DB_SCHEMA="${DB_SCHEMA:-quimioanalytics}"

APPLY_SCHEMA="${APPLY_SCHEMA:-1}"     # 1=aplica schema, 0=não aplica
INSTALL_DEPS="${INSTALL_DEPS:-1}"     # 1=instala deps, 0=não instala
START_DOCKER="${START_DOCKER:-1}"     # 1=sobe containers SQL, 0=não sobe
PIP_INSTALL_MODE="${PIP_INSTALL_MODE:-user}"  # user=instala em ~/.local, system=instala global

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

IDENT_FILE="${IDENT_FILE:-data/identificacao.xlsx}"
ABUND_FILE="${ABUND_FILE:-data/abundancia.xlsx}"

export DB_USER DB_PASSWORD DB_HOST DB_PORT DB_NAME DB_SCHEMA

echo "[INFO] Configuração"
echo "  DB_HOST=${DB_HOST}"
echo "  DB_PORT=${DB_PORT}"
echo "  DB_NAME=${DB_NAME}"
echo "  DB_SCHEMA=${DB_SCHEMA}"
echo "  START_DOCKER=${START_DOCKER}"
echo "  APPLY_SCHEMA=${APPLY_SCHEMA}"
echo "  INSTALL_DEPS=${INSTALL_DEPS}"
echo "  PIP_INSTALL_MODE=${PIP_INSTALL_MODE}"

if [[ "${START_DOCKER}" == "1" ]]; then
  echo "[INFO] Iniciando containers SQL (PostgreSQL + Adminer)..."
  command -v docker >/dev/null 2>&1 || { echo "[ERRO] docker não encontrado"; exit 1; }
  docker compose -f "${COMPOSE_FILE}" up -d postgres adminer
  docker compose -f "${COMPOSE_FILE}" ps
fi

echo "[INFO] Validando Python..."
PYTHON_CMD="${PYTHON_CMD:-python}"
if ! command -v "${PYTHON_CMD}" >/dev/null 2>&1; then
  echo "[WARN] ${PYTHON_CMD} não encontrado, tentando python3..."
  PYTHON_CMD="python3"
  if ! command -v "${PYTHON_CMD}" >/dev/null 2>&1; then
    echo "[ERRO] Nenhum interpretador Python encontrado (python ou python3)"
    exit 1
  fi
fi

echo "[INFO] Usando Python: ${PYTHON_CMD}"

PIP_CMD=("${PYTHON_CMD}" -m pip)
if ! "${PIP_CMD[@]}" --version >/dev/null 2>&1; then
  echo "[ERRO] pip não está disponível para ${PYTHON_CMD}."
  echo "[DICA] Instale pip no sistema para seguir sem virtualenv."
  exit 1
fi

if [[ "${INSTALL_DEPS}" == "1" ]]; then
  echo "[INFO] Instalando dependências..."
  if [[ "${PIP_INSTALL_MODE}" == "user" ]]; then
    "${PIP_CMD[@]}" install --user -r requirements.txt
  else
    "${PIP_CMD[@]}" install -r requirements.txt
  fi
fi

if [[ "${APPLY_SCHEMA}" == "1" ]]; then
  echo "[INFO] Aplicando schema PostgreSQL (database_schema_postgresql.sql)..."
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
"${PYTHON_CMD}" main.py

echo "[OK] Pipeline concluído."
