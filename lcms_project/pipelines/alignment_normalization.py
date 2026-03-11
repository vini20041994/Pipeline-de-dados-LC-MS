"""Pipeline stage for LC-MS alignment and normalization across samples."""

from __future__ import annotations

import argparse
import csv
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class SampleFeaturePoint:
    """A detected feature point from a specific sample."""

    sample_id: str
    mz: float
    rt: float
    intensity: float


@dataclass(frozen=True)
class AlignedIntensityRecord:
    """Feature aligned between samples with raw and normalized intensity."""

    aligned_feature_id: str
    sample_id: str
    mz: float
    rt: float
    raw_intensity: float
    normalized_intensity: float


def read_sample_features(input_file: Path) -> list[SampleFeaturePoint]:
    """Read sample features from CSV with columns sample_id, mz, rt, intensity."""
    if not input_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    required = {"sample_id", "mz", "rt", "intensity"}
    rows: list[SampleFeaturePoint] = []

    with input_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Input CSV must contain columns: sample_id, mz, rt, intensity")

        for row in reader:
            rows.append(
                SampleFeaturePoint(
                    sample_id=row["sample_id"],
                    mz=float(row["mz"]),
                    rt=float(row["rt"]),
                    intensity=float(row["intensity"]),
                )
            )

    return rows


def align_features(
    points: Sequence[SampleFeaturePoint],
    mz_tolerance: float = 0.01,
    rt_tolerance: float = 0.2,
) -> list[tuple[str, list[SampleFeaturePoint], float, float]]:
    """Group nearby points into aligned features across samples."""
    ordered = sorted(points, key=lambda p: p.intensity, reverse=True)
    assigned = [False] * len(ordered)
    groups: list[tuple[str, list[SampleFeaturePoint], float, float]] = []

    for idx, seed in enumerate(ordered):
        if assigned[idx]:
            continue

        cluster: list[SampleFeaturePoint] = []
        weighted_mz = 0.0
        weighted_rt = 0.0
        total = 0.0

        for jdx, point in enumerate(ordered):
            if assigned[jdx]:
                continue
            if abs(point.mz - seed.mz) <= mz_tolerance and abs(point.rt - seed.rt) <= rt_tolerance:
                assigned[jdx] = True
                cluster.append(point)
                weighted_mz += point.mz * point.intensity
                weighted_rt += point.rt * point.intensity
                total += point.intensity

        if not cluster:
            continue

        centroid_mz = weighted_mz / total
        centroid_rt = weighted_rt / total
        group_id = f"AF{len(groups) + 1:05d}"
        groups.append((group_id, cluster, centroid_mz, centroid_rt))

    return groups


def normalize_intensities(groups: Sequence[tuple[str, list[SampleFeaturePoint], float, float]]) -> list[AlignedIntensityRecord]:
    """Normalize by total ion current (TIC) scaling to median sample TIC."""
    totals: dict[str, float] = {}
    for _, cluster, _, _ in groups:
        for point in cluster:
            totals[point.sample_id] = totals.get(point.sample_id, 0.0) + point.intensity

    if not totals:
        return []

    target = statistics.median(totals.values())
    scales = {sample: (target / total if total > 0 else 1.0) for sample, total in totals.items()}

    records: list[AlignedIntensityRecord] = []
    for group_id, cluster, mz, rt in groups:
        for point in cluster:
            records.append(
                AlignedIntensityRecord(
                    aligned_feature_id=group_id,
                    sample_id=point.sample_id,
                    mz=round(mz, 6),
                    rt=round(rt, 4),
                    raw_intensity=round(point.intensity, 4),
                    normalized_intensity=round(point.intensity * scales[point.sample_id], 4),
                )
            )

    return sorted(records, key=lambda r: (r.aligned_feature_id, r.sample_id))


def write_aligned_long(records: Sequence[AlignedIntensityRecord], output_file: Path) -> None:
    """Write long-format aligned and normalized data."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(AlignedIntensityRecord.__dataclass_fields__.keys())
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def write_aligned_matrix(records: Sequence[AlignedIntensityRecord], output_file: Path) -> None:
    """Write wide matrix: one row per aligned feature, one column per sample."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    samples = sorted({record.sample_id for record in records})
    grouped: dict[str, dict[str, float]] = {}
    mz_rt: dict[str, tuple[float, float]] = {}

    for record in records:
        grouped.setdefault(record.aligned_feature_id, {})[record.sample_id] = record.normalized_intensity
        mz_rt[record.aligned_feature_id] = (record.mz, record.rt)

    fieldnames = ["aligned_feature_id", "mz", "rt", *samples]
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for feature_id in sorted(grouped):
            mz, rt = mz_rt[feature_id]
            row = {"aligned_feature_id": feature_id, "mz": mz, "rt": rt}
            for sample in samples:
                row[sample] = grouped[feature_id].get(sample, 0.0)
            writer.writerow(row)


def run_alignment_normalization(
    input_file: Path,
    output_long: Path,
    output_matrix: Path,
    mz_tolerance: float = 0.01,
    rt_tolerance: float = 0.2,
) -> list[AlignedIntensityRecord]:
    """Execute alignment and normalization stage."""
    points = read_sample_features(input_file=input_file)
    groups = align_features(points=points, mz_tolerance=mz_tolerance, rt_tolerance=rt_tolerance)
    records = normalize_intensities(groups=groups)
    write_aligned_long(records=records, output_file=output_long)
    write_aligned_matrix(records=records, output_file=output_matrix)
    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS alignment and normalization")
    parser.add_argument("--input", default="data/processed/sample_features.csv", help="Input CSV with sample_id,mz,rt,intensity")
    parser.add_argument("--output-long", default="data/processed/aligned_features_long.csv", help="Long output CSV")
    parser.add_argument("--output-matrix", default="data/processed/aligned_feature_matrix.csv", help="Wide matrix output CSV")
    parser.add_argument("--mz-tolerance", type=float, default=0.01, help="m/z tolerance for alignment")
    parser.add_argument("--rt-tolerance", type=float, default=0.2, help="Retention-time tolerance for alignment")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for alignment and normalization stage."""
    args = _parse_args()
    records = run_alignment_normalization(
        input_file=Path(args.input),
        output_long=Path(args.output_long),
        output_matrix=Path(args.output_matrix),
        mz_tolerance=args.mz_tolerance,
        rt_tolerance=args.rt_tolerance,
    )
    print(f"Aligned {len(records)} record(s). Outputs: {args.output_long}, {args.output_matrix}")


if __name__ == "__main__":
    main()
