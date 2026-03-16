from etl.extract import extract_abundance, extract_identification
from etl.transform import clean_identification, merge_datasets, transform_abundance
from etl.score import calculate_score, select_top5
from etl.enrich import enrich_dataframe
from etl.load import Loader
from config.database import get_engine


def run_pipeline(
    identification_path: str = "data/identificacao.xlsx",
    abundance_path: str = "data/abundancia.xlsx",
    experiment_name: str = "LC-MS Batch 001",
    instrument: str = "LC-MS",
):
    print("[1/6] Extraindo planilhas...")
    ident_df = extract_identification(identification_path)
    abundance_df = extract_abundance(abundance_path)

    print("[2/6] Limpando e transformando...")
    ident_df = clean_identification(ident_df)
    abundance_df = transform_abundance(abundance_df)
    merged_df = merge_datasets(ident_df, abundance_df)

    print("[3/6] Calculando score probabilístico...")
    scored_df = calculate_score(merged_df)

    print("[4/6] Selecionando Top 5 por sinal...")
    top5_df = select_top5(scored_df)

    print("[5/6] Enriquecendo metadados via PubChem...")
    enriched_df = enrich_dataframe(top5_df)

    print("[6/6] Persistindo no PostgreSQL...")
    loader = Loader(get_engine(), experiment_name=experiment_name, instrument=instrument)
    loader.load(enriched_df)

    print("Pipeline finalizado com sucesso.")


if __name__ == "__main__":
    run_pipeline()
