"""HTTP API for orchestrating the LC-MS pipeline."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from lcms_project.pipelines.alignment_normalization import run_alignment_normalization
from lcms_project.pipelines.annotation import run_annotation
from lcms_project.pipelines.conversion import DEFAULT_SOURCE_EXTENSIONS, run_conversion
from lcms_project.pipelines.enrichment import run_enrichment
from lcms_project.pipelines.feature_detection import run_feature_detection
from lcms_project.pipelines.ingestion import DEFAULT_ALLOWED_EXTENSIONS, run_ingestion
from lcms_project.pipelines.ranking import run_ranking
from lcms_project.pipelines.storage import run_storage

app = FastAPI(
    title="LC-MS Pipeline API",
    description="API para executar cada etapa da pipeline LC-MS e o fluxo completo.",
    version="1.0.0",
)


class IngestionRequest(BaseModel):
    raw_dir: str = "data/raw"
    output_file: str = "data/processed/ingestion_manifest.json"
    allowed_extensions: list[str] = Field(default_factory=lambda: list(DEFAULT_ALLOWED_EXTENSIONS))


class ConversionRequest(BaseModel):
    input_dir: str = "data/raw"
    output_dir: str = "data/mzml"
    source_extensions: list[str] = Field(default_factory=lambda: list(DEFAULT_SOURCE_EXTENSIONS))
    msconvert_bin: str = "msconvert"
    dry_run: bool = False


class FeatureDetectionRequest(BaseModel):
    input_file: str = "data/mzml/points.csv"
    output_file: str = "data/processed/feature_table.csv"
    intensity_threshold: float = 1000.0
    mz_tolerance: float = 0.01
    rt_tolerance: float = 0.2


class AlignmentRequest(BaseModel):
    input_file: str = "data/processed/sample_features.csv"
    output_long: str = "data/processed/aligned_features_long.csv"
    output_matrix: str = "data/processed/aligned_feature_matrix.csv"
    mz_tolerance: float = 0.01
    rt_tolerance: float = 0.2


class AnnotationRequest(BaseModel):
    feature_file: str = "data/processed/feature_table.csv"
    library_file: str = "data/reference/compound_library.csv"
    output_file: str = "data/processed/candidates.csv"
    ppm_tolerance: float = 10.0
    top_k: int = 5


class EnrichmentRequest(BaseModel):
    candidate_file: str = "data/processed/candidates.csv"
    output_file: str = "data/processed/enriched_candidates.csv"
    dry_run: bool = False
    timeout_s: int = 15
    capability_output: str | None = "data/processed/enrichment_source_capabilities.csv"


class RankingRequest(BaseModel):
    input_file: str = "data/processed/enriched_candidates.csv"
    output_file: str = "data/processed/scored_candidates.csv"
    top_k_file: str = "data/processed/top5_candidates.csv"
    sigma_ppm: float = 5.0
    alpha_msms: float = 1.0
    w_db: float = 1 / 3
    w_taxonomy: float = 1 / 3
    w_ontology: float = 1 / 3
    top_k: int = 5


class StorageRequest(BaseModel):
    db_path: str = "data/warehouse/lcms.db"
    scored_file: str = "data/processed/scored_candidates.csv"
    enriched_file: str = "data/processed/enriched_candidates.csv"


class FullPipelineRequest(BaseModel):
    raw_dir: str = "data/raw"
    mzml_dir: str = "data/mzml"
    processed_dir: str = "data/processed"
    reference_library: str = "data/reference/compound_library.csv"
    db_path: str = "data/warehouse/lcms.db"
    dry_run_conversion: bool = False
    dry_run_enrichment: bool = False


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def _handle_pipeline_error(exc: Exception) -> None:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/pipeline/ingestion")
def ingestion(payload: IngestionRequest) -> dict[str, object]:
    try:
        records = run_ingestion(
            raw_dir=Path(payload.raw_dir),
            output_file=Path(payload.output_file),
            allowed_extensions=payload.allowed_extensions,
        )
        return {"records": [asdict(item) for item in records], "count": len(records)}
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/conversion")
def conversion(payload: ConversionRequest) -> dict[str, object]:
    try:
        records = run_conversion(
            input_dir=Path(payload.input_dir),
            output_dir=Path(payload.output_dir),
            source_extensions=payload.source_extensions,
            msconvert_bin=payload.msconvert_bin,
            dry_run=payload.dry_run,
        )
        return {"records": [asdict(item) for item in records], "count": len(records)}
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/feature-detection")
def feature_detection(payload: FeatureDetectionRequest) -> dict[str, object]:
    try:
        records = run_feature_detection(
            input_file=Path(payload.input_file),
            output_file=Path(payload.output_file),
            intensity_threshold=payload.intensity_threshold,
            mz_tolerance=payload.mz_tolerance,
            rt_tolerance=payload.rt_tolerance,
        )
        return {"records": [asdict(item) for item in records], "count": len(records)}
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/alignment")
def alignment(payload: AlignmentRequest) -> dict[str, object]:
    try:
        records = run_alignment_normalization(
            input_file=Path(payload.input_file),
            output_long=Path(payload.output_long),
            output_matrix=Path(payload.output_matrix),
            mz_tolerance=payload.mz_tolerance,
            rt_tolerance=payload.rt_tolerance,
        )
        return {"records": [asdict(item) for item in records], "count": len(records)}
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/annotation")
def annotation(payload: AnnotationRequest) -> dict[str, object]:
    try:
        records = run_annotation(
            feature_file=Path(payload.feature_file),
            library_file=Path(payload.library_file),
            output_file=Path(payload.output_file),
            ppm_tolerance=payload.ppm_tolerance,
            top_k=payload.top_k,
        )
        return {"records": [asdict(item) for item in records], "count": len(records)}
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/enrichment")
def enrichment(payload: EnrichmentRequest) -> dict[str, object]:
    try:
        records = run_enrichment(
            candidate_file=Path(payload.candidate_file),
            output_file=Path(payload.output_file),
            dry_run=payload.dry_run,
            timeout_s=payload.timeout_s,
            capability_output=Path(payload.capability_output) if payload.capability_output else None,
        )
        return {"records": [asdict(item) for item in records], "count": len(records)}
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/ranking")
def ranking(payload: RankingRequest) -> dict[str, object]:
    try:
        records = run_ranking(
            input_file=Path(payload.input_file),
            output_file=Path(payload.output_file),
            top_k_file=Path(payload.top_k_file),
            sigma_ppm=payload.sigma_ppm,
            alpha_msms=payload.alpha_msms,
            w_db=payload.w_db,
            w_taxonomy=payload.w_taxonomy,
            w_ontology=payload.w_ontology,
            top_k=payload.top_k,
        )
        return {"records": [asdict(item) for item in records], "count": len(records)}
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/storage")
def storage(payload: StorageRequest) -> dict[str, int]:
    try:
        features, candidates, metadata = run_storage(
            db_path=Path(payload.db_path),
            scored_file=Path(payload.scored_file),
            enriched_file=Path(payload.enriched_file),
        )
        return {
            "features_inserted": features,
            "candidates_inserted": candidates,
            "metadata_inserted": metadata,
        }
    except Exception as exc:
        _handle_pipeline_error(exc)


@app.post("/pipeline/run")
def run_full_pipeline(payload: FullPipelineRequest) -> dict[str, object]:
    try:
        processed_dir = Path(payload.processed_dir)
        ingestion_records = run_ingestion(Path(payload.raw_dir), processed_dir / "ingestion_manifest.json")
        conversion_records = run_conversion(
            input_dir=Path(payload.raw_dir),
            output_dir=Path(payload.mzml_dir),
            dry_run=payload.dry_run_conversion,
        )
        feature_records = run_feature_detection(
            input_file=Path(payload.mzml_dir) / "points.csv",
            output_file=processed_dir / "feature_table.csv",
        )
        alignment_records = run_alignment_normalization(
            input_file=processed_dir / "sample_features.csv",
            output_long=processed_dir / "aligned_features_long.csv",
            output_matrix=processed_dir / "aligned_feature_matrix.csv",
        )
        annotation_records = run_annotation(
            feature_file=processed_dir / "feature_table.csv",
            library_file=Path(payload.reference_library),
            output_file=processed_dir / "candidates.csv",
        )
        enrichment_records = run_enrichment(
            candidate_file=processed_dir / "candidates.csv",
            output_file=processed_dir / "enriched_candidates.csv",
            dry_run=payload.dry_run_enrichment,
            capability_output=processed_dir / "enrichment_source_capabilities.csv",
        )
        ranking_records = run_ranking(
            input_file=processed_dir / "enriched_candidates.csv",
            output_file=processed_dir / "scored_candidates.csv",
            top_k_file=processed_dir / "top5_candidates.csv",
        )
        storage_counts = run_storage(
            db_path=Path(payload.db_path),
            scored_file=processed_dir / "scored_candidates.csv",
            enriched_file=processed_dir / "enriched_candidates.csv",
        )
        return {
            "summary": {
                "ingestion_count": len(ingestion_records),
                "conversion_count": len(conversion_records),
                "feature_count": len(feature_records),
                "alignment_count": len(alignment_records),
                "annotation_count": len(annotation_records),
                "enrichment_count": len(enrichment_records),
                "ranking_count": len(ranking_records),
                "storage": {
                    "features_inserted": storage_counts[0],
                    "candidates_inserted": storage_counts[1],
                    "metadata_inserted": storage_counts[2],
                },
            }
        }
    except Exception as exc:
        _handle_pipeline_error(exc)
