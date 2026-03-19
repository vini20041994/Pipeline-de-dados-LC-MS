"""Orquestrador principal do pipeline QuimioAnalytics.

Funcionamento:
1) Extrai planilhas de identificação e abundância.
2) Executa limpeza/transformação e merge dos dados.
3) Calcula score probabilístico e seleciona Top 5 por sinal.
4) Enriquece candidatos com metadados de bases públicas.
5) Persiste o resultado no PostgreSQL.
6) Gera saídas de auditoria em `outputs/` para cada etapa do ETL.

Bibliotecas utilizadas:
- Módulos locais: etl.extract, etl.transform, etl.score, etl.enrich, etl.load.
- Módulo local de configuração: config.database.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from etl.extract import extract_abundance, extract_identification
from etl.transform import clean_identification, merge_datasets, transform_abundance
from etl.score import calculate_score, select_top5
from etl.enrich import enrich_dataframe
from etl.load import Loader
from config.database import get_engine


OUTPUT_DIR = Path("outputs")


def _save_stage_output(df: pd.DataFrame, filename: str) -> None:
    """Salva DataFrame da etapa ETL em CSV para auditoria local."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / filename
    df.to_csv(out_path, index=False)
    print(f"  -> saída gerada: {out_path} ({len(df)} linhas)")


def _save_load_summary(summary: dict) -> None:
    """Salva resumo da carga no banco em arquivo JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "06_load_summary.json"
    with out_path.open("w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)
    print(f"  -> saída gerada: {out_path}")


def run_pipeline(
    identification_path: str = "data/identificacao.xlsx",
    abundance_path: str = "data/abundancia.xlsx",
    experiment_name: str = "LC-MS Batch 001",
    instrument: str = "LC-MS",
):
    """Executa o pipeline ETL completo de identificação LC-MS.

    Args:
        identification_path: Caminho da planilha com candidatos por sinal.
        abundance_path: Caminho da planilha com abundância por replicata.
        experiment_name: Nome lógico do experimento salvo no banco.
        instrument: Instrumento analítico associado ao experimento.
    """
    print("[1/6] Extraindo planilhas...")
    ident_df = extract_identification(identification_path)
    abundance_df = extract_abundance(abundance_path)
    _save_stage_output(ident_df, "01_extract_identification.csv")
    _save_stage_output(abundance_df, "01_extract_abundance.csv")

    print("[2/6] Limpando e transformando...")
    ident_df = clean_identification(ident_df)
    abundance_df = transform_abundance(abundance_df)
    merged_df = merge_datasets(ident_df, abundance_df)
    _save_stage_output(ident_df, "02_transform_identification.csv")
    _save_stage_output(abundance_df, "02_transform_abundance.csv")
    _save_stage_output(merged_df, "02_transform_merged.csv")

    print("[3/6] Calculando score probabilístico...")
    scored_df = calculate_score(merged_df)
    _save_stage_output(scored_df, "03_score_scored.csv")

    print("[4/6] Selecionando Top 5 por sinal...")
    top5_df = select_top5(scored_df)
    _save_stage_output(top5_df, "04_score_top5.csv")

    print("[5/6] Enriquecendo metadados via PubChem...")
    enriched_df = enrich_dataframe(top5_df)
    _save_stage_output(enriched_df, "05_enrich_enriched.csv")

    print("[6/6] Persistindo no PostgreSQL...")
    loader = Loader(get_engine(), experiment_name=experiment_name, instrument=instrument)
    load_summary = loader.load(enriched_df)
    _save_load_summary(load_summary)

    print("Pipeline finalizado com sucesso.")


if __name__ == "__main__":
    run_pipeline()
