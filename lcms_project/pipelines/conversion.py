"""Pipeline stage for LC-MS format conversion to mzML.

This module converts proprietary raw files (e.g. .raw) into mzML using
ProteoWizard's ``msconvert`` utility.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

DEFAULT_SOURCE_EXTENSIONS = (".raw",)


@dataclass(frozen=True)
class ConversionRecord:
    """Represents one conversion attempt and its outcome."""

    source_file: str
    output_file: str
    status: str
    message: str


def discover_source_files(input_dir: Path, source_extensions: Sequence[str]) -> list[Path]:
    """Discover source files recursively under ``input_dir``."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    normalized_extensions = {ext.lower() for ext in source_extensions}
    files = [
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in normalized_extensions
    ]
    return sorted(files)


def build_output_file(source_file: Path, input_dir: Path, output_dir: Path) -> Path:
    """Build output mzML path preserving directory structure."""
    relative_path = source_file.relative_to(input_dir)
    return (output_dir / relative_path).with_suffix(".mzML")


def convert_file(source_file: Path, output_file: Path, msconvert_bin: str, dry_run: bool = False) -> ConversionRecord:
    """Convert one source file to mzML via ``msconvert``."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        return ConversionRecord(
            source_file=str(source_file.resolve()),
            output_file=str(output_file.resolve()),
            status="dry_run",
            message="Conversion skipped (--dry-run)",
        )

    command = [msconvert_bin, str(source_file), "--mzML", "--outdir", str(output_file.parent)]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return ConversionRecord(
            source_file=str(source_file.resolve()),
            output_file=str(output_file.resolve()),
            status="converted",
            message="OK",
        )
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        return ConversionRecord(
            source_file=str(source_file.resolve()),
            output_file=str(output_file.resolve()),
            status="failed",
            message=stderr or f"msconvert exited with code {error.returncode}",
        )


def write_conversion_report(records: Sequence[ConversionRecord], report_file: Path) -> None:
    """Write conversion report as JSON or CSV based on extension."""
    report_file.parent.mkdir(parents=True, exist_ok=True)

    if report_file.suffix.lower() == ".json":
        report_file.write_text(
            json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    if report_file.suffix.lower() == ".csv":
        fieldnames = list(ConversionRecord.__dataclass_fields__.keys())
        with report_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(asdict(record) for record in records)
        return

    raise ValueError("Unsupported report extension. Use .json or .csv")


def run_conversion(
    input_dir: Path,
    output_dir: Path,
    source_extensions: Sequence[str] = DEFAULT_SOURCE_EXTENSIONS,
    msconvert_bin: str = "msconvert",
    dry_run: bool = False,
) -> list[ConversionRecord]:
    """Execute conversion stage and return per-file outcomes."""
    if not dry_run and shutil.which(msconvert_bin) is None:
        raise FileNotFoundError(
            f"Could not find '{msconvert_bin}' in PATH. Install ProteoWizard or provide --msconvert-bin"
        )

    source_files = discover_source_files(input_dir=input_dir, source_extensions=source_extensions)
    records: list[ConversionRecord] = []

    for source_file in source_files:
        output_file = build_output_file(source_file=source_file, input_dir=input_dir, output_dir=output_dir)
        records.append(convert_file(source_file=source_file, output_file=output_file, msconvert_bin=msconvert_bin, dry_run=dry_run))

    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS format conversion to mzML")
    parser.add_argument("--input-dir", default="data/raw", help="Directory with proprietary raw files")
    parser.add_argument("--output-dir", default="data/mzml", help="Directory for mzML files")
    parser.add_argument(
        "--source-ext",
        nargs="+",
        default=list(DEFAULT_SOURCE_EXTENSIONS),
        help="Source file extensions to convert",
    )
    parser.add_argument("--msconvert-bin", default="msconvert", help="Path/name of msconvert executable")
    parser.add_argument("--dry-run", action="store_true", help="Do not execute msconvert; only simulate conversions")
    parser.add_argument(
        "--report",
        default="data/processed/conversion_report.json",
        help="Path to conversion report (.json or .csv)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for format conversion stage."""
    args = _parse_args()
    records = run_conversion(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        source_extensions=args.source_ext,
        msconvert_bin=args.msconvert_bin,
        dry_run=args.dry_run,
    )
    write_conversion_report(records=records, report_file=Path(args.report))

    converted = sum(record.status == "converted" for record in records)
    failed = sum(record.status == "failed" for record in records)
    dry_run_count = sum(record.status == "dry_run" for record in records)

    print(
        f"Processed {len(records)} file(s): converted={converted}, failed={failed}, dry_run={dry_run_count}. "
        f"Report: {args.report}"
    )


if __name__ == "__main__":
    main()
