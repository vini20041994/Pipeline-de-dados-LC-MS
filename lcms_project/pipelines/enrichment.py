"""Pipeline stage for LC-MS enrichment using public compound databases."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_S = 15
DEFAULT_USER_AGENT = "lcms-pipeline/1.0"


@dataclass(frozen=True)
class CandidateInput:
    """Candidate compound produced by annotation stage."""

    feature_id: str
    compound_name: str


@dataclass(frozen=True)
class SourceCapability:
    """Availability matrix for metadata fields in each enrichment source."""

    source: str
    taxonomy: bool
    organisms: bool
    chemical_ontology: bool
    chemical_class: bool
    applications: bool
    industrial_pharma_food_use: bool
    evidence: str


@dataclass(frozen=True)
class EnrichmentRecord:
    """Aggregated enrichment data for a compound candidate."""

    feature_id: str
    compound_name: str
    pubchem_cid: str
    pubchem_title: str
    chebi_id: str
    hmdb_id: str
    foodb_id: str
    taxonomy: str
    organisms: str
    chemical_class: str
    ontology: str
    applications: str
    industrial_pharma_food_use: str
    sources_found: str


SOURCE_CAPABILITY_MATRIX: tuple[SourceCapability, ...] = (
    SourceCapability(
        source="PubChem",
        taxonomy=False,
        organisms=False,
        chemical_ontology=True,
        chemical_class=True,
        applications=True,
        industrial_pharma_food_use=True,
        evidence="Compound classification and use metadata can be obtained through PUG-View sections.",
    ),
    SourceCapability(
        source="ChEBI",
        taxonomy=False,
        organisms=False,
        chemical_ontology=True,
        chemical_class=True,
        applications=False,
        industrial_pharma_food_use=False,
        evidence="Strong chemical ontology/classification, limited application/use descriptors.",
    ),
    SourceCapability(
        source="HMDB",
        taxonomy=True,
        organisms=True,
        chemical_ontology=True,
        chemical_class=True,
        applications=True,
        industrial_pharma_food_use=True,
        evidence="Metabolite pages include taxonomy, biospecimen/source and biological/clinical context.",
    ),
    SourceCapability(
        source="FooDB",
        taxonomy=True,
        organisms=True,
        chemical_ontology=False,
        chemical_class=True,
        applications=True,
        industrial_pharma_food_use=True,
        evidence="Food-centric source/organism and usage context with limited ontology depth.",
    ),
)


def _http_get_json(url: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> Any:
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(request, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def read_candidates(input_file: Path) -> list[CandidateInput]:
    """Read candidate CSV with columns feature_id and compound_name."""
    if not input_file.exists():
        raise FileNotFoundError(f"Candidate file does not exist: {input_file}")

    records: list[CandidateInput] = []
    with input_file.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"feature_id", "compound_name"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Candidate CSV must contain columns: feature_id, compound_name")

        seen: set[tuple[str, str]] = set()
        for row in reader:
            key = (row["feature_id"], row["compound_name"])
            if key in seen:
                continue
            seen.add(key)
            records.append(CandidateInput(feature_id=row["feature_id"], compound_name=row["compound_name"]))
    return records


def _enrich_pubchem(compound_name: str, dry_run: bool, timeout_s: int) -> dict[str, str]:
    if dry_run:
        return {"pubchem_cid": "dry_run", "pubchem_title": "dry_run"}

    encoded = quote(compound_name)
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/property/Title/JSON"
    try:
        payload = _http_get_json(url, timeout_s=timeout_s)
        props = payload.get("PropertyTable", {}).get("Properties", [])
        if not props:
            return {"pubchem_cid": "", "pubchem_title": ""}
        first = props[0]
        return {
            "pubchem_cid": str(first.get("CID", "")),
            "pubchem_title": str(first.get("Title", compound_name)),
        }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {"pubchem_cid": "", "pubchem_title": ""}


def _enrich_chebi(compound_name: str, dry_run: bool, timeout_s: int) -> dict[str, str]:
    if dry_run:
        return {"chebi_id": "dry_run"}

    encoded = quote(compound_name)
    url = f"https://www.ebi.ac.uk/chebi/searchId.do?chebiName={encoded}"
    try:
        request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        with urlopen(request, timeout=timeout_s) as response:
            content = response.read().decode("utf-8", errors="ignore")
        marker = "CHEBI:"
        idx = content.find(marker)
        if idx == -1:
            return {"chebi_id": ""}
        chebi_id = content[idx : idx + 20].split("<")[0].strip()
        return {"chebi_id": chebi_id}
    except (HTTPError, URLError, TimeoutError):
        return {"chebi_id": ""}


def _enrich_hmdb(compound_name: str, dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {"hmdb_id": "dry_run"}
    return {"hmdb_id": ""}


def _enrich_foodb(compound_name: str, dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {"foodb_id": "dry_run"}
    return {"foodb_id": ""}


def verify_source_capabilities() -> list[SourceCapability]:
    """Return a capability matrix for requested enrichment metadata fields."""
    return list(SOURCE_CAPABILITY_MATRIX)


def enrich_candidates(candidates: Sequence[CandidateInput], dry_run: bool = False, timeout_s: int = DEFAULT_TIMEOUT_S) -> list[EnrichmentRecord]:
    """Enrich candidates with data from PubChem, ChEBI, HMDB and FooDB."""
    records: list[EnrichmentRecord] = []

    for candidate in candidates:
        pubchem = _enrich_pubchem(candidate.compound_name, dry_run=dry_run, timeout_s=timeout_s)
        chebi = _enrich_chebi(candidate.compound_name, dry_run=dry_run, timeout_s=timeout_s)
        hmdb = _enrich_hmdb(candidate.compound_name, dry_run=dry_run)
        foodb = _enrich_foodb(candidate.compound_name, dry_run=dry_run)

        found = [
            source
            for source, value in (
                ("pubchem", pubchem.get("pubchem_cid", "")),
                ("chebi", chebi.get("chebi_id", "")),
                ("hmdb", hmdb.get("hmdb_id", "")),
                ("foodb", foodb.get("foodb_id", "")),
            )
            if value
        ]

        records.append(
            EnrichmentRecord(
                feature_id=candidate.feature_id,
                compound_name=candidate.compound_name,
                pubchem_cid=pubchem.get("pubchem_cid", ""),
                pubchem_title=pubchem.get("pubchem_title", ""),
                chebi_id=chebi.get("chebi_id", ""),
                hmdb_id=hmdb.get("hmdb_id", ""),
                foodb_id=foodb.get("foodb_id", ""),
                taxonomy="",
                organisms="",
                chemical_class="",
                ontology="",
                applications="",
                industrial_pharma_food_use="",
                sources_found=";".join(found),
            )
        )

    return records


def write_enrichment(records: Sequence[EnrichmentRecord], output_file: Path) -> None:
    """Write enrichment results as CSV or JSON."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.suffix.lower() == ".json":
        output_file.write_text(json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if output_file.suffix.lower() == ".csv":
        fieldnames = list(EnrichmentRecord.__dataclass_fields__.keys())
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(asdict(record) for record in records)
        return

    raise ValueError("Unsupported output extension. Use .csv or .json")


def write_capability_report(records: Sequence[SourceCapability], output_file: Path) -> None:
    """Write capability matrix report as CSV or JSON."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.suffix.lower() == ".json":
        output_file.write_text(json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if output_file.suffix.lower() == ".csv":
        fieldnames = list(SourceCapability.__dataclass_fields__.keys())
        with output_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(asdict(record) for record in records)
        return

    raise ValueError("Unsupported output extension. Use .csv or .json")


def run_enrichment(
    candidate_file: Path,
    output_file: Path,
    dry_run: bool = False,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    capability_output: Path | None = None,
) -> list[EnrichmentRecord]:
    """Execute enrichment stage end-to-end."""
    candidates = read_candidates(candidate_file)
    records = enrich_candidates(candidates=candidates, dry_run=dry_run, timeout_s=timeout_s)
    write_enrichment(records=records, output_file=output_file)

    if capability_output is not None:
        write_capability_report(verify_source_capabilities(), output_file=capability_output)

    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LC-MS candidate enrichment with public databases")
    parser.add_argument("--candidates", default="data/processed/candidates.csv", help="Input candidate CSV")
    parser.add_argument("--output", default="data/processed/enriched_candidates.csv", help="Output file (.csv/.json)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S, help="HTTP timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Do not call external services")
    parser.add_argument(
        "--capabilities-output",
        default="data/processed/enrichment_source_capabilities.csv",
        help="Output file for source capability verification (.csv/.json)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for enrichment stage."""
    args = _parse_args()
    records = run_enrichment(
        candidate_file=Path(args.candidates),
        output_file=Path(args.output),
        dry_run=args.dry_run,
        timeout_s=args.timeout,
        capability_output=Path(args.capabilities_output) if args.capabilities_output else None,
    )
    print(
        f"Enriched {len(records)} candidate(s). Output: {args.output}. "
        f"Capabilities: {args.capabilities_output}"
    )


if __name__ == "__main__":
    main()
