import pandas as pd


REQUIRED_IDENT_COLUMNS = {
    "sample_code",
    "signal_id",
    "signal_key",
    "mz",
    "retention_time",
    "intensity",
    "molecule_name",
    "fragmentation_score",
    "base_score",
    "isotope_score",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = out.columns.str.strip().str.lower()
    return out


def clean_identification(df: pd.DataFrame) -> pd.DataFrame:
    out = _normalize_columns(df)

    missing = REQUIRED_IDENT_COLUMNS - set(out.columns)
    if missing:
        raise ValueError(f"Missing required identification columns: {sorted(missing)}")

    out = out.dropna(subset=["sample_code", "signal_id", "molecule_name"]).copy()
    return out


def transform_abundance(df: pd.DataFrame) -> pd.DataFrame:
    out = _normalize_columns(df)
    if "signal_id" not in out.columns:
        raise ValueError("Abundance sheet must contain 'signal_id' column")

    replicate_columns = [c for c in out.columns if c != "signal_id"]
    if not replicate_columns:
        raise ValueError("Abundance sheet must contain at least one replicate column")

    melted = out.melt(
        id_vars=["signal_id"],
        value_vars=replicate_columns,
        var_name="replicate",
        value_name="abundance",
    )

    melted["replicate_number"] = (
        melted["replicate"].astype(str).str.extract(r"(\d+)").fillna("1").astype(int)
    )
    return melted[["signal_id", "replicate", "replicate_number", "abundance"]]


def merge_datasets(ident_df: pd.DataFrame, abundance_df: pd.DataFrame) -> pd.DataFrame:
    merged = ident_df.merge(abundance_df, on="signal_id", how="left")
    return merged
