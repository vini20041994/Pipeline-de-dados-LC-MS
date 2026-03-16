from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

import requests
from tqdm import tqdm


PUBCHEM_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
    "{name}/property/MolecularFormula,ExactMass,CID/JSON"
)
KEGG_FIND_URL = "https://rest.kegg.jp/find/compound/{name}"
OLS_SEARCH_URL = "https://www.ebi.ac.uk/ols4/api/search"
HMDB_SEARCH_URL = "https://hmdb.ca/unearth/q"
MESH_LOOKUP_URL = "https://id.nlm.nih.gov/mesh/lookup/descriptor"


@dataclass
class EnrichmentRecord:
    pubchem_cid: int | None = None
    formula: str | None = None
    exact_mass: float | None = None
    kegg_id: str | None = None
    chebi_id: str | None = None
    hmdb_id: str | None = None
    mesh_id: str | None = None
    mesh_tree: str | None = None


class MultiDBEnrichmentClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._cache: dict[str, EnrichmentRecord] = {}

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        response = requests.get(url, params=params, timeout=self.timeout)
        if response.status_code != 200:
            return None
        return response.json()

    def _get_text(self, url: str, params: dict[str, Any] | None = None) -> str | None:
        response = requests.get(url, params=params, timeout=self.timeout)
        if response.status_code != 200:
            return None
        return response.text

    def _pubchem(self, query: str, rec: EnrichmentRecord) -> None:
        payload = self._get_json(PUBCHEM_URL.format(name=requests.utils.quote(query)))
        if not payload:
            return
        try:
            props = payload["PropertyTable"]["Properties"][0]
            rec.pubchem_cid = props.get("CID")
            rec.formula = props.get("MolecularFormula")
            rec.exact_mass = props.get("ExactMass")
        except Exception:
            return

    def _kegg(self, query: str, rec: EnrichmentRecord) -> None:
        text = self._get_text(KEGG_FIND_URL.format(name=requests.utils.quote(query)))
        if not text:
            return
        first = text.splitlines()[0] if text.splitlines() else ""
        if not first:
            return
        # Ex: cpd:C00031\tD-Glucose; ...
        rec.kegg_id = first.split("\t", 1)[0].replace("cpd:", "")

    def _chebi(self, query: str, rec: EnrichmentRecord) -> None:
        payload = self._get_json(
            OLS_SEARCH_URL,
            params={"q": query, "ontology": "chebi", "rows": 1},
        )
        if not payload:
            return
        docs = payload.get("response", {}).get("docs", [])
        if not docs:
            return
        obo_id = docs[0].get("obo_id") or docs[0].get("short_form")
        if obo_id:
            rec.chebi_id = str(obo_id).replace("CHEBI:", "CHEBI:")

    def _hmdb(self, query: str, rec: EnrichmentRecord) -> None:
        text = self._get_text(HMDB_SEARCH_URL, params={"query": query, "searcher": "metabolites"})
        if not text:
            return
        # Busca primeiro HMDB id no HTML
        match = re.search(r"HMDB\d{5,}", text)
        if match:
            rec.hmdb_id = match.group(0)

    def _mesh(self, query: str, rec: EnrichmentRecord) -> None:
        payload = self._get_json(
            MESH_LOOKUP_URL,
            params={"label": query, "match": "contains", "limit": 1},
        )
        if not payload:
            return
        first = payload[0] if isinstance(payload, list) and payload else None
        if not first:
            return

        resource = first.get("resource")  # ex: http://id.nlm.nih.gov/mesh/D012345
        if resource:
            rec.mesh_id = resource.rsplit("/", 1)[-1]
            # tentativa best-effort de obter treeNumber
            mesh_payload = self._get_json(f"{resource}.json")
            if isinstance(mesh_payload, dict):
                tree = mesh_payload.get("treeNumber")
                if isinstance(tree, list) and tree:
                    rec.mesh_tree = str(tree[0])
                elif isinstance(tree, str):
                    rec.mesh_tree = tree

    def get_compound(self, compound_name: str) -> EnrichmentRecord:
        key = str(compound_name).strip().lower()
        if not key:
            return EnrichmentRecord()
        if key in self._cache:
            return self._cache[key]

        rec = EnrichmentRecord()
        for fn in (self._pubchem, self._kegg, self._chebi, self._hmdb, self._mesh):
            try:
                fn(key, rec)
            except Exception:
                continue

        self._cache[key] = rec
        return rec


def enrich_dataframe(df):
    client = MultiDBEnrichmentClient()

    pubchem_cids = []
    formulas = []
    exact_masses = []
    kegg_ids = []
    chebi_ids = []
    hmdb_ids = []
    mesh_ids = []
    mesh_trees = []

    for name in tqdm(df["molecule_name"], desc="Enrichment (PubChem/KEGG/ChEBI/HMDB/MeSH)"):
        rec = client.get_compound(str(name))
        pubchem_cids.append(rec.pubchem_cid)
        formulas.append(rec.formula)
        exact_masses.append(rec.exact_mass)
        kegg_ids.append(rec.kegg_id)
        chebi_ids.append(rec.chebi_id)
        hmdb_ids.append(rec.hmdb_id)
        mesh_ids.append(rec.mesh_id)
        mesh_trees.append(rec.mesh_tree)

    out = df.copy()
    out["pubchem_cid"] = pubchem_cids
    out["formula"] = formulas
    out["exact_mass"] = exact_masses
    out["kegg_id"] = kegg_ids
    out["chebi_id"] = chebi_ids
    out["hmdb_id"] = hmdb_ids
    out["mesh_id"] = mesh_ids
    out["mesh_tree"] = mesh_trees
    return out
