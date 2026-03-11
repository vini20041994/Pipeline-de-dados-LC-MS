#!/usr/bin/env bash
set -euo pipefail

RAW_DIR="data/raw"
MZML_DIR="data/mzml"
PROCESSED_DIR="data/processed"
REFERENCE_LIBRARY="data/reference/compound_library.csv"
DB_PATH="data/warehouse/lcms.db"
DRY_RUN_CONVERSION=0
DRY_RUN_ENRICHMENT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --raw-dir)
      RAW_DIR="$2"; shift 2 ;;
    --mzml-dir)
      MZML_DIR="$2"; shift 2 ;;
    --processed-dir)
      PROCESSED_DIR="$2"; shift 2 ;;
    --reference-library)
      REFERENCE_LIBRARY="$2"; shift 2 ;;
    --db-path)
      DB_PATH="$2"; shift 2 ;;
    --dry-run-conversion)
      DRY_RUN_CONVERSION=1; shift ;;
    --dry-run-enrichment)
      DRY_RUN_ENRICHMENT=1; shift ;;
    -h|--help)
      cat <<'EOF'
Uso: ./run_pipeline.sh [opções]

Opções:
  --raw-dir <dir>             Diretório de entrada com arquivos brutos (default: data/raw)
  --mzml-dir <dir>            Diretório de saída mzML (default: data/mzml)
  --processed-dir <dir>       Diretório de artefatos processados (default: data/processed)
  --reference-library <file>  Biblioteca de compostos para anotação (default: data/reference/compound_library.csv)
  --db-path <file>            Caminho do banco SQLite de saída (default: data/warehouse/lcms.db)
  --dry-run-conversion        Não chama msconvert na etapa de conversão
  --dry-run-enrichment        Não chama APIs externas na etapa de enriquecimento
  -h, --help                  Mostra esta ajuda
EOF
      exit 0 ;;
    *)
      echo "Opção desconhecida: $1" >&2
      exit 1 ;;
  esac
done

echo "[1/8] Ingestão"
python -m lcms_project.pipelines.ingestion \
  --raw-dir "$RAW_DIR" \
  --output "$PROCESSED_DIR/ingestion_manifest.json"

echo "[2/8] Conversão para mzML"
CONVERSION_CMD=(
  python -m lcms_project.pipelines.conversion
  --input-dir "$RAW_DIR"
  --output-dir "$MZML_DIR"
  --report "$PROCESSED_DIR/conversion_report.json"
)
if [[ $DRY_RUN_CONVERSION -eq 1 ]]; then
  CONVERSION_CMD+=(--dry-run)
fi
"${CONVERSION_CMD[@]}"

echo "[3/8] Detecção de features"
python -m lcms_project.pipelines.feature_detection \
  --input "$MZML_DIR/points.csv" \
  --output "$PROCESSED_DIR/feature_table.csv"

echo "[4/8] Alinhamento e normalização"
python -m lcms_project.pipelines.alignment_normalization \
  --input "$PROCESSED_DIR/sample_features.csv" \
  --output-long "$PROCESSED_DIR/aligned_features_long.csv" \
  --output-matrix "$PROCESSED_DIR/aligned_feature_matrix.csv"

echo "[5/8] Anotação de candidatos"
python -m lcms_project.pipelines.annotation \
  --features "$PROCESSED_DIR/feature_table.csv" \
  --library "$REFERENCE_LIBRARY" \
  --output "$PROCESSED_DIR/candidates.csv"

echo "[6/8] Enriquecimento"
ENRICH_CMD=(
  python -m lcms_project.pipelines.enrichment
  --candidates "$PROCESSED_DIR/candidates.csv"
  --output "$PROCESSED_DIR/enriched_candidates.csv"
  --capabilities-output "$PROCESSED_DIR/enrichment_source_capabilities.csv"
)
if [[ $DRY_RUN_ENRICHMENT -eq 1 ]]; then
  ENRICH_CMD+=(--dry-run)
fi
"${ENRICH_CMD[@]}"

echo "[7/8] Scoring e Top-K"
python -m lcms_project.pipelines.ranking \
  --input "$PROCESSED_DIR/enriched_candidates.csv" \
  --output "$PROCESSED_DIR/scored_candidates.csv" \
  --top-output "$PROCESSED_DIR/top5_candidates.csv"

echo "[8/8] Armazenamento em banco"
python -m lcms_project.pipelines.storage \
  --db "$DB_PATH" \
  --scored "$PROCESSED_DIR/scored_candidates.csv" \
  --enriched "$PROCESSED_DIR/enriched_candidates.csv"

echo "Pipeline finalizado com sucesso."
