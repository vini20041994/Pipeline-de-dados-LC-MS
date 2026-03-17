#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------
# QuimioAnalytics - Start SQL stack (Postgres + Adminer)
# -----------------------------------------------------
# Este script:
# 1) valida a existência do Docker/Compose
# 2) sobe os serviços SQL do docker-compose
# 3) imprime instruções rápidas de acesso
# -----------------------------------------------------

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

command -v docker >/dev/null 2>&1 || {
  echo "[ERRO] docker não encontrado no PATH"
  exit 1
}

echo "[INFO] Subindo stack SQL com ${COMPOSE_FILE}..."
docker compose -f "${COMPOSE_FILE}" up -d postgres adminer

echo "[INFO] Status dos serviços:"
docker compose -f "${COMPOSE_FILE}" ps

echo "[OK] Stack SQL iniciada."
echo "[INFO] Adminer: http://localhost:8080"
echo "[INFO] PostgreSQL (host): localhost:55432"
