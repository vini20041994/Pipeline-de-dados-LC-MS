#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------
# QuimioAnalytics - Execução completa (SQL + ETL)
# -----------------------------------------------------
# Este script orquestra o fluxo completo:
# 1) sobe stack SQL (docker)
# 2) aplica schema
# 3) executa pipeline ETL Python
# -----------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

"${SCRIPT_DIR}/start_sql_stack.sh"
"${SCRIPT_DIR}/apply_schema.sh"

# Evita reaplicar schema novamente no run_pipeline.sh
APPLY_SCHEMA=0 "${SCRIPT_DIR}/run_pipeline.sh"

echo "[OK] Fluxo completo finalizado."
