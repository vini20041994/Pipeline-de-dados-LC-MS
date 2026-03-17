import numpy as np
import pandas as pd


def normalize(series: pd.Series) -> pd.Series:
    """Normaliza uma série numérica no intervalo [0, 1].

    Args:
        series: Série contendo valores de score.

    Returns:
        Série normalizada, ou zeros quando não há variação.
    """
    series = pd.to_numeric(series, errors="coerce")
    min_v = series.min()
    max_v = series.max()
    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - min_v) / (max_v - min_v)


def _safe_prior(series: pd.Series) -> pd.Series:
    """Gera prior não nulo e normalizado por sinal.

    Args:
        series: Série de score base normalizado por candidato.

    Returns:
        Série de probabilidades a priori com soma 1 por grupo.
    """
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    s = s + 1e-9
    total = s.sum()
    if total <= 0:
        return pd.Series(np.full(len(s), 1 / max(len(s), 1)), index=s.index)
    return s / total


def calculate_score(
    df: pd.DataFrame,
    w1: float = 0.4,
    w2: float = 0.4,
    w3: float = 0.2,
) -> pd.DataFrame:
    """
    Mathematical model (Top-5 heuristic):

      P(C_i | S_frag, S_base, S_iso)
      = P(S_frag, S_base, S_iso | C_i) * P(C_i) / P(S_frag, S_base, S_iso)

      Score_final(C_i)
      = w1 * S_frag_hat + w2 * S_base_hat + w3 * S_iso_hat

    Implementation notes:
    - Priors P(C_i) are estimated from normalized base score within each signal.
    - Likelihood term uses multiplicative evidences from normalized metrics.
    - Evidence denominator is computed per signal to produce posterior probabilities.

    Args:
        df: DataFrame com scores de fragmentação, base e isótopo.
        w1: Peso aplicado ao score de fragmentação normalizado.
        w2: Peso aplicado ao score base normalizado.
        w3: Peso aplicado ao score isotópico normalizado.

    Returns:
        DataFrame com colunas de score final, probabilidade e ranking.
    """
    out = df.copy()

    out["normalized_frag_score"] = normalize(out["fragmentation_score"])
    out["normalized_base_score"] = normalize(out["base_score"])
    out["normalized_iso_score"] = normalize(out["isotope_score"])

    out["final_score"] = (
        w1 * out["normalized_frag_score"]
        + w2 * out["normalized_base_score"]
        + w3 * out["normalized_iso_score"]
    )

    out["prior_probability"] = (
        out.groupby("signal_id")["normalized_base_score"].transform(_safe_prior)
    )

    out["likelihood"] = (
        (out["normalized_frag_score"] + 1e-9)
        * (out["normalized_base_score"] + 1e-9)
        * (out["normalized_iso_score"] + 1e-9)
    )

    out["numerator"] = out["likelihood"] * out["prior_probability"]
    evidence = out.groupby("signal_id")["numerator"].transform("sum")
    out["posterior_probability"] = np.where(evidence > 0, out["numerator"] / evidence, 0.0)

    out["probability"] = out["posterior_probability"]

    out["ranking"] = (
        out.groupby("signal_id")["final_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    return out


def select_top5(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra os candidatos Top 5 por sinal.

    Args:
        df: DataFrame com coluna `ranking` já calculada.

    Returns:
        Apenas linhas com ranking menor ou igual a 5.
    """
    return df[df["ranking"] <= 5].copy()
