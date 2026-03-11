"""Pipeline stage for LC-MS data ingestion.

This module is responsible for discovering raw LC-MS files and materializing
an ingestion manifest that can be consumed by downstream stages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_ALLOWED_EXTENSIONS = (".raw", ".mzML", ".mzXML")


@dataclass(frozen=True)
class IngestionRecord:
    """Represents one ingested file and its metadata."""

    sample_id: str
    file_name: str
    file_path: str
    file_size_bytes: int
    sha256: str
    ingested_at_utc: str


def _compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 hash of a file."""
    digest = hashlib.sha256()
    with file_path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _to_sample_id(file_path: Path) -> str:
    """Derive a sample ID from the filename without extension."""
    return file_path.stem


def discover_raw_files(raw_dir: Path, allowed_extensions: Sequence[str]) -> list[Path]:
    """Discover raw files recursively under ``raw_dir``."""
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw directory does not exist: {raw_dir}")

    normalized_extensions = {ext.lower() for ext in allowed_extensions}
    files = [
        path
        for path in raw_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in normalized_extensions
    ]
    return sorted(files)


def create_ingestion_records(files: Iterable[Path]) -> list[IngestionRecord]:
    """Build ingestion records from paths."""
    ingested_at = datetime.now(timezone.utc).isoformat()
    records: list[IngestionRecord] = []

    for file_path in files:
        records.append(
            IngestionRecord(
                sample_id=_to_sample_id(file_path),
                file_name=file_path.name,
                file_path=str(file_path.resolve()),
                file_size_bytes=file_path.stat().st_size,
                sha256=_compute_sha256(file_path),
                ingested_at_utc=ingested_at,
            )
        )

    return records


def write_manifest(records: Sequence[IngestionRecord], output_file: Path) -> None:
    """Write records to ``output_file`` as JSON or CSV based on extension."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.suffix.lower() == ".json":
        payload = [asdict(record) for record in records]
        output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if output_file.suffix.lower() == ".csv":
        fieldnames = list(IngestionRecord.__dataclass_fields__.keys())
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(asdict(record) for record in records)
        return

    raise ValueError("Unsupported manifest extension. Use .json or .csv")


def run_ingestion(
    raw_dir: Path,
    output_file: Path,
    allowed_extensions: Sequence[str] = DEFAULT_ALLOWED_EXTENSIONS,
) -> list[IngestionRecord]:
    """Execute ingestion stage and return generated records."""
    files = discover_raw_files(raw_dir=raw_dir, allowed_extensions=allowed_extensions)
    records = create_ingestion_records(files)
    write_manifest(records=records, output_file=output_file)
    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS raw data ingestion")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory with raw files")
    parser.add_argument(
        "--output",
        default="data/processed/ingestion_manifest.json",
        help="Path to generated ingestion manifest (.json or .csv)",
    )
    parser.add_argument(
        "--ext",
        nargs="+",
        default=list(DEFAULT_ALLOWED_EXTENSIONS),
        help="Allowed file extensions to ingest",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for ingestion step."""
    args = _parse_args()
    records = run_ingestion(raw_dir=Path(args.raw_dir), output_file=Path(args.output), allowed_extensions=args.ext)
    print(f"Ingested {len(records)} file(s). Manifest: {args.output}")


if __name__ == "__main__":
    main()
