"""Pipeline stage for LC-MS Bayesian scoring and candidate ranking."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


DEFAULT_W_DB = 1 / 3
DEFAULT_W_TAXONOMY = 1 / 3
DEFAULT_W_ONTOLOGY = 1 / 3


@dataclass(frozen=True)
class RankedCandidate:
    """Candidate with Bayesian components and normalized final score."""

    feature_id: str
    compound_name: str
    mass_error_ppm: float
    p_mass: float
    p_msms: float
    p_isotope: float
    p_prior: float
    score_raw: float
    score_norm: float
    rank: int


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _safe_float(value: str | None, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    return float(value)


def _parse_bool_like(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "sim"}:
        return True
    if normalized in {"0", "false", "no", "n", "nao", "não"}:
        return False
    return None


def _mass_error_ppm(row: dict[str, str], sigma_ppm: float) -> float:
    if row.get("mass_error_ppm") not in (None, ""):
        return abs(_safe_float(row.get("mass_error_ppm")))

    mz_obs = _safe_float(row.get("mz_observed"), default=0.0)
    mz_theo = _safe_float(row.get("mz_theoretical"), default=0.0)
    if mz_theo <= 0:
        return sigma_ppm
    return abs((mz_obs - mz_theo) / mz_theo) * 1_000_000


def _p_mass(error_ppm: float, sigma_ppm: float) -> float:
    return _clamp01(math.exp(-(abs(error_ppm) / max(sigma_ppm, 1e-9))))


def _p_msms(row: dict[str, str], alpha: float) -> float:
    cosine = _clamp01(_safe_float(row.get("msms_similarity"), default=0.0))
    return _clamp01(cosine**alpha)


def _p_isotope(row: dict[str, str]) -> float:
    if row.get("isotope_similarity") not in (None, ""):
        return _clamp01(_safe_float(row.get("isotope_similarity"), default=0.0))

    delta = _safe_float(row.get("isotope_delta"), default=1.0)
    return _clamp01(1.0 - abs(delta))


def _taxonomy_score(row: dict[str, str]) -> float:
    explicit = _parse_bool_like(row.get("taxonomy_match"))
    if explicit is True:
        return 1.0
    if explicit is False:
        return 0.0
    return 0.7 if ((row.get("taxonomy") or "").strip() or (row.get("organisms") or "").strip()) else 0.0


def _ontology_score(row: dict[str, str]) -> float:
    explicit = _parse_bool_like(row.get("ontology_match"))
    if explicit is True:
        return 1.0
    if explicit is False:
        return 0.0
    return 0.7 if ((row.get("ontology") or "").strip() or (row.get("chemical_class") or "").strip()) else 0.0


def _db_score(row: dict[str, str]) -> float:
    sources = [x.strip() for x in (row.get("sources_found") or "").split(";") if x.strip()]
    return _clamp01(len(set(sources)) / 4.0)


def _p_prior(row: dict[str, str], w_db: float, w_taxonomy: float, w_ontology: float) -> float:
    total = w_db + w_taxonomy + w_ontology
    if total <= 0:
        raise ValueError("Prior weights must sum to a positive number")
    w_db, w_taxonomy, w_ontology = w_db / total, w_taxonomy / total, w_ontology / total
    prior = (w_db * _db_score(row)) + (w_taxonomy * _taxonomy_score(row)) + (w_ontology * _ontology_score(row))
    return _clamp01(prior)


def read_candidates(input_file: Path) -> list[dict[str, str]]:
    if not input_file.exists():
        raise FileNotFoundError(f"Candidate input does not exist: {input_file}")
    with input_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"feature_id", "compound_name"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Input CSV must contain columns: feature_id, compound_name")
        return list(reader)


def score_candidates(
    rows: Sequence[dict[str, str]],
    sigma_ppm: float = 5.0,
    alpha_msms: float = 1.0,
    w_db: float = DEFAULT_W_DB,
    w_taxonomy: float = DEFAULT_W_TAXONOMY,
    w_ontology: float = DEFAULT_W_ONTOLOGY,
) -> list[RankedCandidate]:
    by_feature_raw: dict[str, list[RankedCandidate]] = {}

    for row in rows:
        error_ppm = _mass_error_ppm(row, sigma_ppm=sigma_ppm)
        p_mass = _p_mass(error_ppm, sigma_ppm=sigma_ppm)
        p_msms = _p_msms(row, alpha=alpha_msms)
        p_isotope = _p_isotope(row)
        p_prior = _p_prior(row, w_db=w_db, w_taxonomy=w_taxonomy, w_ontology=w_ontology)

        score_raw = p_mass * p_msms * p_isotope * p_prior

        candidate = RankedCandidate(
            feature_id=row["feature_id"],
            compound_name=row["compound_name"],
            mass_error_ppm=round(error_ppm, 6),
            p_mass=round(p_mass, 6),
            p_msms=round(p_msms, 6),
            p_isotope=round(p_isotope, 6),
            p_prior=round(p_prior, 6),
            score_raw=round(score_raw, 10),
            score_norm=0.0,
            rank=0,
        )
        by_feature_raw.setdefault(candidate.feature_id, []).append(candidate)

    ranked: list[RankedCandidate] = []
    for _, candidates in by_feature_raw.items():
        normalizer = sum(c.score_raw for c in candidates)
        normalized = [
            RankedCandidate(
                feature_id=c.feature_id,
                compound_name=c.compound_name,
                mass_error_ppm=c.mass_error_ppm,
                p_mass=c.p_mass,
                p_msms=c.p_msms,
                p_isotope=c.p_isotope,
                p_prior=c.p_prior,
                score_raw=c.score_raw,
                score_norm=round((c.score_raw / normalizer) if normalizer > 0 else 0.0, 10),
                rank=0,
            )
            for c in candidates
        ]

        ordered = sorted(normalized, key=lambda c: c.score_norm, reverse=True)
        for idx, c in enumerate(ordered, start=1):
            ranked.append(
                RankedCandidate(
                    feature_id=c.feature_id,
                    compound_name=c.compound_name,
                    mass_error_ppm=c.mass_error_ppm,
                    p_mass=c.p_mass,
                    p_msms=c.p_msms,
                    p_isotope=c.p_isotope,
                    p_prior=c.p_prior,
                    score_raw=c.score_raw,
                    score_norm=c.score_norm,
                    rank=idx,
                )
            )

    return sorted(ranked, key=lambda c: (c.feature_id, c.rank))


def write_ranked(rows: Sequence[RankedCandidate], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(RankedCandidate.__dataclass_fields__.keys())
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_top_k(rows: Sequence[RankedCandidate], top_k_file: Path, k: int = 5) -> None:
    top_k_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(RankedCandidate.__dataclass_fields__.keys())
    with top_k_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            if row.rank <= k:
                writer.writerow(asdict(row))


def run_ranking(
    input_file: Path,
    output_file: Path,
    top_k_file: Path,
    sigma_ppm: float = 5.0,
    alpha_msms: float = 1.0,
    w_db: float = DEFAULT_W_DB,
    w_taxonomy: float = DEFAULT_W_TAXONOMY,
    w_ontology: float = DEFAULT_W_ONTOLOGY,
    top_k: int = 5,
) -> list[RankedCandidate]:
    rows = read_candidates(input_file)
    ranked = score_candidates(
        rows,
        sigma_ppm=sigma_ppm,
        alpha_msms=alpha_msms,
        w_db=w_db,
        w_taxonomy=w_taxonomy,
        w_ontology=w_ontology,
    )
    write_ranked(ranked, output_file=output_file)
    write_top_k(ranked, top_k_file=top_k_file, k=top_k)
    return ranked


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS Bayesian candidate scoring and ranking")
    parser.add_argument("--input", default="data/processed/enriched_candidates.csv", help="Input candidate CSV")
    parser.add_argument("--output", default="data/processed/scored_candidates.csv", help="Output scored CSV")
    parser.add_argument("--top-output", default="data/processed/top5_candidates.csv", help="Output top-k CSV")
    parser.add_argument("--sigma-ppm", type=float, default=5.0, help="Instrument tolerance σ for mass probability")
    parser.add_argument("--alpha-msms", type=float, default=1.0, help="Exponent α for cosine spectral similarity")
    parser.add_argument("--w-db", type=float, default=DEFAULT_W_DB, help="Prior weight for database evidence")
    parser.add_argument("--w-taxonomy", type=float, default=DEFAULT_W_TAXONOMY, help="Prior weight for taxonomy evidence")
    parser.add_argument("--w-ontology", type=float, default=DEFAULT_W_ONTOLOGY, help="Prior weight for ontology evidence")
    parser.add_argument("--top-k", type=int, default=5, help="Top-k candidates per feature")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    ranked = run_ranking(
        input_file=Path(args.input),
        output_file=Path(args.output),
        top_k_file=Path(args.top_output),
        sigma_ppm=args.sigma_ppm,
        alpha_msms=args.alpha_msms,
        w_db=args.w_db,
        w_taxonomy=args.w_taxonomy,
        w_ontology=args.w_ontology,
        top_k=args.top_k,
    )
    print(f"Scored {len(ranked)} candidate(s). Outputs: {args.output}, {args.top_output}")


if __name__ == "__main__":
    main()
