from pathlib import Path
import pandas as pd


def extract_identification(path: str | Path) -> pd.DataFrame:
    """Lê a planilha de identificação de moléculas.

    Args:
        path: Caminho para o arquivo Excel de identificação.

    Returns:
        DataFrame com os dados brutos de identificação.
    """
    return pd.read_excel(path)


def extract_abundance(path: str | Path) -> pd.DataFrame:
    """Lê a planilha de abundância por sinal.

    Args:
        path: Caminho para o arquivo Excel de abundância.

    Returns:
        DataFrame com os dados brutos de abundância.
    """
    return pd.read_excel(path)
