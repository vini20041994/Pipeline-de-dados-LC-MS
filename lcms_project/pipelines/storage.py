"""Pipeline stage for persisting LC-MS outputs into a relational database."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Any


DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS features (
    feature_id TEXT PRIMARY KEY,
    mz REAL NOT NULL,
    retention_time REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS compound_candidates (
    candidate_pk INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id TEXT NOT NULL,
    compound_name TEXT NOT NULL,
    score_raw REAL,
    score_norm REAL,
    rank INTEGER,
    FOREIGN KEY(feature_id) REFERENCES features(feature_id)
);

CREATE TABLE IF NOT EXISTS compound_metadata (
    metadata_pk INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id TEXT NOT NULL,
    compound_name TEXT NOT NULL,
    taxonomy TEXT,
    organisms TEXT,
    ontology_class TEXT,
    chemical_class TEXT,
    applications TEXT,
    industrial_use TEXT,
    sources_found TEXT,
    FOREIGN KEY(feature_id) REFERENCES features(feature_id)
);
"""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _require_columns(rows: list[dict[str, str]], required: set[str], file_label: str) -> None:
    if not rows:
        return
    present = set(rows[0].keys())
    missing = required - present
    if missing:
        raise ValueError(f"Missing columns in {file_label}: {sorted(missing)}")


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or str(value).strip() == "":
        return default
    return float(value)


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(float(value))


def _upsert_features(conn: sqlite3.Connection, scored_rows: list[dict[str, str]]) -> int:
    features: dict[str, tuple[float, float]] = {}
    for row in scored_rows:
        feature_id = row["feature_id"]
        mz = _to_float(row.get("mz") or row.get("mz_observed"), 0.0)
        rt = _to_float(row.get("rt") or row.get("retention_time"), 0.0)
        features[feature_id] = (mz, rt)

    conn.executemany(
        """
        INSERT INTO features(feature_id, mz, retention_time)
        VALUES (?, ?, ?)
        ON CONFLICT(feature_id) DO UPDATE SET
            mz = excluded.mz,
            retention_time = excluded.retention_time
        """,
        [(fid, vals[0], vals[1]) for fid, vals in features.items()],
    )
    return len(features)


def _replace_candidates(conn: sqlite3.Connection, scored_rows: list[dict[str, str]]) -> int:
    conn.execute("DELETE FROM compound_candidates")
    payload = [
        (
            row["feature_id"],
            row["compound_name"],
            _to_float(row.get("score_raw"), 0.0),
            _to_float(row.get("score_norm"), 0.0),
            _to_int(row.get("rank"), 0),
        )
        for row in scored_rows
    ]
    conn.executemany(
        """
        INSERT INTO compound_candidates(feature_id, compound_name, score_raw, score_norm, rank)
        VALUES (?, ?, ?, ?, ?)
        """,
        payload,
    )
    return len(payload)


def _replace_metadata(conn: sqlite3.Connection, enriched_rows: list[dict[str, str]]) -> int:
    conn.execute("DELETE FROM compound_metadata")
    payload = [
        (
            row["feature_id"],
            row["compound_name"],
            row.get("taxonomy", ""),
            row.get("organisms", ""),
            row.get("ontology", ""),
            row.get("chemical_class", ""),
            row.get("applications", ""),
            row.get("industrial_pharma_food_use", ""),
            row.get("sources_found", ""),
        )
        for row in enriched_rows
    ]
    conn.executemany(
        """
        INSERT INTO compound_metadata(
            feature_id, compound_name, taxonomy, organisms,
            ontology_class, chemical_class, applications, industrial_use, sources_found
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    return len(payload)


def run_storage(db_path: Path, scored_file: Path, enriched_file: Path) -> tuple[int, int, int]:
    scored_rows = _read_csv(scored_file)
    enriched_rows = _read_csv(enriched_file)

    _require_columns(scored_rows, {"feature_id", "compound_name", "score_norm", "rank"}, "scored_file")
    _require_columns(enriched_rows, {"feature_id", "compound_name"}, "enriched_file")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(DDL_SQLITE)
        features_n = _upsert_features(conn, scored_rows)
        candidates_n = _replace_candidates(conn, scored_rows)
        metadata_n = _replace_metadata(conn, enriched_rows)
        conn.commit()

    return features_n, candidates_n, metadata_n


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS storage stage (SQLite)")
    parser.add_argument("--db", default="data/warehouse/lcms.db", help="SQLite database path")
    parser.add_argument("--scored", default="data/processed/scored_candidates.csv", help="Scored candidates CSV")
    parser.add_argument("--enriched", default="data/processed/enriched_candidates.csv", help="Enriched candidates CSV")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    features_n, candidates_n, metadata_n = run_storage(
        db_path=Path(args.db),
        scored_file=Path(args.scored),
        enriched_file=Path(args.enriched),
    )
    print(
        f"Stored features={features_n}, candidates={candidates_n}, metadata={metadata_n} in {args.db}"
    )


if __name__ == "__main__":
    main()
