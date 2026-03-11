"""Pipeline stage for LC-MS feature detection.

This module performs a lightweight feature detection over tabular LC-MS points
containing at least ``mz``, ``rt`` (retention time) and ``intensity`` columns.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class SpectrumPoint:
    """One LC-MS point in (mz, rt, intensity) space."""

    mz: float
    rt: float
    intensity: float


@dataclass(frozen=True)
class FeatureRecord:
    """Detected feature metadata."""

    feature_id: str
    mz: float
    rt: float
    intensity: float
    point_count: int


def read_points(input_file: Path) -> list[SpectrumPoint]:
    """Read spectrum points from CSV file.

    The CSV must contain headers: ``mz``, ``rt`` and ``intensity``.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    points: list[SpectrumPoint] = []
    with input_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"mz", "rt", "intensity"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Input CSV must contain columns: mz, rt, intensity")

        for row in reader:
            points.append(
                SpectrumPoint(
                    mz=float(row["mz"]),
                    rt=float(row["rt"]),
                    intensity=float(row["intensity"]),
                )
            )

    return points


def detect_features(
    points: Sequence[SpectrumPoint],
    intensity_threshold: float = 1000.0,
    mz_tolerance: float = 0.01,
    rt_tolerance: float = 0.2,
) -> list[FeatureRecord]:
    """Detect local maxima and cluster nearby points into LC-MS features."""
    candidates = [point for point in points if point.intensity >= intensity_threshold]
    candidates.sort(key=lambda point: point.intensity, reverse=True)

    features: list[FeatureRecord] = []
    assigned = [False] * len(candidates)

    for idx, seed in enumerate(candidates):
        if assigned[idx]:
            continue

        cluster_indexes: list[int] = []
        weighted_mz = 0.0
        weighted_rt = 0.0
        total_intensity = 0.0
        max_intensity = seed.intensity

        for jdx, point in enumerate(candidates):
            if assigned[jdx]:
                continue
            if abs(point.mz - seed.mz) <= mz_tolerance and abs(point.rt - seed.rt) <= rt_tolerance:
                assigned[jdx] = True
                cluster_indexes.append(jdx)
                weighted_mz += point.mz * point.intensity
                weighted_rt += point.rt * point.intensity
                total_intensity += point.intensity
                if point.intensity > max_intensity:
                    max_intensity = point.intensity

        if not cluster_indexes:
            continue

        centroid_mz = weighted_mz / total_intensity
        centroid_rt = weighted_rt / total_intensity
        feature_id = f"F{len(features) + 1:05d}"
        features.append(
            FeatureRecord(
                feature_id=feature_id,
                mz=round(centroid_mz, 6),
                rt=round(centroid_rt, 4),
                intensity=round(max_intensity, 2),
                point_count=len(cluster_indexes),
            )
        )

    return sorted(features, key=lambda feature: feature.intensity, reverse=True)


def write_features(features: Sequence[FeatureRecord], output_file: Path) -> None:
    """Write detected features as CSV or JSON based on output extension."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.suffix.lower() == ".json":
        output_file.write_text(
            json.dumps([asdict(feature) for feature in features], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    if output_file.suffix.lower() == ".csv":
        fieldnames = list(FeatureRecord.__dataclass_fields__.keys())
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(asdict(feature) for feature in features)
        return

    raise ValueError("Unsupported output extension. Use .csv or .json")


def run_feature_detection(
    input_file: Path,
    output_file: Path,
    intensity_threshold: float = 1000.0,
    mz_tolerance: float = 0.01,
    rt_tolerance: float = 0.2,
) -> list[FeatureRecord]:
    """Execute feature detection end-to-end."""
    points = read_points(input_file=input_file)
    features = detect_features(
        points=points,
        intensity_threshold=intensity_threshold,
        mz_tolerance=mz_tolerance,
        rt_tolerance=rt_tolerance,
    )
    write_features(features=features, output_file=output_file)
    return features


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS feature detection from tabular points")
    parser.add_argument("--input", default="data/mzml/points.csv", help="Input CSV with mz, rt and intensity")
    parser.add_argument("--output", default="data/processed/feature_table.csv", help="Output feature file (.csv/.json)")
    parser.add_argument("--intensity-threshold", type=float, default=1000.0, help="Minimum intensity to keep a point")
    parser.add_argument("--mz-tolerance", type=float, default=0.01, help="m/z tolerance for clustering")
    parser.add_argument("--rt-tolerance", type=float, default=0.2, help="Retention time tolerance for clustering")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for feature detection stage."""
    args = _parse_args()
    features = run_feature_detection(
        input_file=Path(args.input),
        output_file=Path(args.output),
        intensity_threshold=args.intensity_threshold,
        mz_tolerance=args.mz_tolerance,
        rt_tolerance=args.rt_tolerance,
    )
    print(f"Detected {len(features)} feature(s). Output: {args.output}")


if __name__ == "__main__":
    main()
