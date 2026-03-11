"""Pipeline stage for LC-MS candidate annotation.

This module annotates detected/aligned features by matching feature m/z values
against a compound library and assigning candidate scores.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class FeatureInput:
    """Input feature to be annotated."""

    feature_id: str
    mz: float
    rt: float


@dataclass(frozen=True)
class CompoundLibraryEntry:
    """Reference compound used for matching."""

    compound_name: str
    exact_mass: float
    formula: str
    source: str


@dataclass(frozen=True)
class AnnotationRecord:
    """Annotation candidate for one feature."""

    feature_id: str
    mz: float
    rt: float
    compound_name: str
    formula: str
    source: str
    mass_error_ppm: float
    score_mass: float
    rank: int


def read_features(input_file: Path) -> list[FeatureInput]:
    """Read features CSV with columns: feature_id,mz,rt."""
    if not input_file.exists():
        raise FileNotFoundError(f"Feature file does not exist: {input_file}")

    rows: list[FeatureInput] = []
    with input_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"feature_id", "mz", "rt"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Feature CSV must contain columns: feature_id, mz, rt")

        for row in reader:
            rows.append(FeatureInput(feature_id=row["feature_id"], mz=float(row["mz"]), rt=float(row["rt"])))
    return rows


def read_compound_library(library_file: Path) -> list[CompoundLibraryEntry]:
    """Read compound library CSV with columns: compound_name,exact_mass,formula,source."""
    if not library_file.exists():
        raise FileNotFoundError(f"Library file does not exist: {library_file}")

    rows: list[CompoundLibraryEntry] = []
    with library_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"compound_name", "exact_mass", "formula", "source"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Library CSV must contain columns: compound_name, exact_mass, formula, source")

        for row in reader:
            rows.append(
                CompoundLibraryEntry(
                    compound_name=row["compound_name"],
                    exact_mass=float(row["exact_mass"]),
                    formula=row["formula"],
                    source=row["source"],
                )
            )
    return rows


def _mass_error_ppm(observed_mz: float, exact_mass: float) -> float:
    return ((observed_mz - exact_mass) / exact_mass) * 1_000_000


def _score_from_ppm(abs_ppm_error: float, ppm_tolerance: float) -> float:
    if abs_ppm_error > ppm_tolerance:
        return 0.0
    return round(1.0 - (abs_ppm_error / ppm_tolerance), 6)


def annotate_candidates(
    features: Sequence[FeatureInput],
    library: Sequence[CompoundLibraryEntry],
    ppm_tolerance: float = 10.0,
    top_k: int = 5,
) -> list[AnnotationRecord]:
    """Annotate each feature against the library and keep top-k candidates."""
    annotations: list[AnnotationRecord] = []

    for feature in features:
        candidates: list[AnnotationRecord] = []
        for entry in library:
            ppm_error = _mass_error_ppm(feature.mz, entry.exact_mass)
            abs_ppm = abs(ppm_error)
            score_mass = _score_from_ppm(abs_ppm, ppm_tolerance=ppm_tolerance)
            if score_mass <= 0:
                continue
            candidates.append(
                AnnotationRecord(
                    feature_id=feature.feature_id,
                    mz=feature.mz,
                    rt=feature.rt,
                    compound_name=entry.compound_name,
                    formula=entry.formula,
                    source=entry.source,
                    mass_error_ppm=round(ppm_error, 4),
                    score_mass=score_mass,
                    rank=0,
                )
            )

        candidates.sort(key=lambda item: (item.score_mass, -abs(item.mass_error_ppm)), reverse=True)
        for rank, candidate in enumerate(candidates[:top_k], start=1):
            annotations.append(
                AnnotationRecord(
                    feature_id=candidate.feature_id,
                    mz=candidate.mz,
                    rt=candidate.rt,
                    compound_name=candidate.compound_name,
                    formula=candidate.formula,
                    source=candidate.source,
                    mass_error_ppm=candidate.mass_error_ppm,
                    score_mass=candidate.score_mass,
                    rank=rank,
                )
            )

    return annotations


def write_annotations(records: Sequence[AnnotationRecord], output_file: Path) -> None:
    """Write annotation records to CSV or JSON based on extension."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.suffix.lower() == ".json":
        output_file.write_text(json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if output_file.suffix.lower() == ".csv":
        fieldnames = list(AnnotationRecord.__dataclass_fields__.keys())
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(asdict(record) for record in records)
        return

    raise ValueError("Unsupported output extension. Use .csv or .json")


def run_annotation(
    feature_file: Path,
    library_file: Path,
    output_file: Path,
    ppm_tolerance: float = 10.0,
    top_k: int = 5,
) -> list[AnnotationRecord]:
    """Execute candidate annotation end-to-end."""
    features = read_features(feature_file)
    library = read_compound_library(library_file)
    records = annotate_candidates(features=features, library=library, ppm_tolerance=ppm_tolerance, top_k=top_k)
    write_annotations(records=records, output_file=output_file)
    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS candidate annotation by exact-mass matching")
    parser.add_argument("--features", default="data/processed/feature_table.csv", help="Input features CSV")
    parser.add_argument("--library", default="data/reference/compound_library.csv", help="Reference compound library CSV")
    parser.add_argument("--output", default="data/processed/candidates.csv", help="Output candidates file (.csv/.json)")
    parser.add_argument("--ppm-tolerance", type=float, default=10.0, help="Mass error tolerance in ppm")
    parser.add_argument("--top-k", type=int, default=5, help="Max number of candidates per feature")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for candidate annotation stage."""
    args = _parse_args()
    records = run_annotation(
        feature_file=Path(args.features),
        library_file=Path(args.library),
        output_file=Path(args.output),
        ppm_tolerance=args.ppm_tolerance,
        top_k=args.top_k,
    )
    print(f"Generated {len(records)} candidate annotation(s). Output: {args.output}")


if __name__ == "__main__":
    main()
