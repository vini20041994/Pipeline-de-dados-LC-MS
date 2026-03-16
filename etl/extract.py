from pathlib import Path
import pandas as pd


def extract_identification(path: str | Path) -> pd.DataFrame:
    return pd.read_excel(path)


def extract_abundance(path: str | Path) -> pd.DataFrame:
    return pd.read_excel(path)
