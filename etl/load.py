from __future__ import annotations

"""Camada de carga transacional no PostgreSQL.

Funcionamento:
- Recebe DataFrame enriquecido e persiste entidades no modelo relacional.
- Controla inserções em cadeia: experimento, amostra, sinal, candidato, score e probabilidade.
- Utiliza cache local em memória para reduzir duplicações durante a carga.
- Executa em transação única por meio de `engine.begin()`.

Bibliotecas utilizadas:
- pandas: iteração e validações auxiliares em DataFrame.
- sqlalchemy.text: execução de SQL parametrizado com segurança.
"""

import pandas as pd
from sqlalchemy import text


class Loader:
    def __init__(self, engine, experiment_name: str, instrument: str | None = None, description: str | None = None):
        """Configura o carregador para persistência no PostgreSQL.

        Args:
            engine: SQLAlchemy Engine conectado ao banco.
            experiment_name: Nome do experimento para a tabela `experiment`.
            instrument: Instrumento analítico do experimento.
            description: Descrição opcional do experimento.
        """
        self.engine = engine
        self.experiment_name = experiment_name
        self.instrument = instrument
        self.description = description

    def load(self, df: pd.DataFrame) -> None:
        """Persiste dados processados no schema relacional do projeto.

        Args:
            df: DataFrame final com sinais, candidatos, score e enriquecimento.
        """
        with self.engine.begin() as conn:
            experiment_id = conn.execute(
                text(
                    """
                    INSERT INTO experiment (experiment_name, instrument, description)
                    VALUES (:experiment_name, :instrument, :description)
                    RETURNING id_experiment
                    """
                ),
                {
                    "experiment_name": self.experiment_name,
                    "instrument": self.instrument,
                    "description": self.description,
                },
            ).scalar_one()

            sample_cache: dict[str, int] = {}
            signal_cache: dict[tuple[str, str], int] = {}
            molecule_cache: dict[int, int] = {}

            unique_samples = df[["sample_code"]].drop_duplicates()
            for _, row in unique_samples.iterrows():
                sample_id = conn.execute(
                    text(
                        """
                        INSERT INTO sample (id_experiment, sample_code, matrix_type)
                        VALUES (:id_experiment, :sample_code, :matrix_type)
                        RETURNING id_sample
                        """
                    ),
                    {
                        "id_experiment": experiment_id,
                        "sample_code": row["sample_code"],
                        "matrix_type": row.get("matrix_type"),
                    },
                ).scalar_one()
                sample_cache[row["sample_code"]] = sample_id

            signal_cols = ["sample_code", "signal_id", "signal_key", "mz", "retention_time", "intensity"]
            unique_signals = df[signal_cols].drop_duplicates()
            for _, row in unique_signals.iterrows():
                sample_id = sample_cache[row["sample_code"]]
                db_signal_id = conn.execute(
                    text(
                        """
                        INSERT INTO analytical_signal (id_sample, signal_key, mz, retention_time, intensity)
                        VALUES (:id_sample, :signal_key, :mz, :retention_time, :intensity)
                        RETURNING id_signal
                        """
                    ),
                    {
                        "id_sample": sample_id,
                        "signal_key": row.get("signal_key") or str(row["signal_id"]),
                        "mz": row.get("mz"),
                        "retention_time": row.get("retention_time"),
                        "intensity": row.get("intensity"),
                    },
                ).scalar_one()
                signal_cache[(row["sample_code"], str(row["signal_id"]))] = db_signal_id

            replicate_cols = ["sample_code", "signal_id", "replicate_number", "abundance"]
            if all(col in df.columns for col in replicate_cols):
                replicates = df[replicate_cols].dropna(subset=["replicate_number"]).drop_duplicates()
                for _, row in replicates.iterrows():
                    db_signal_id = signal_cache[(row["sample_code"], str(row["signal_id"]))]
                    conn.execute(
                        text(
                            """
                            INSERT INTO signal_replicate (id_signal, replicate_number, abundance)
                            VALUES (:id_signal, :replicate_number, :abundance)
                            """
                        ),
                        {
                            "id_signal": db_signal_id,
                            "replicate_number": int(row["replicate_number"]),
                            "abundance": row.get("abundance"),
                        },
                    )

            for _, row in df.iterrows():
                db_signal_id = signal_cache[(row["sample_code"], str(row["signal_id"]))]

                molecule_id = None
                if pd.notna(row.get("pubchem_cid")):
                    pubchem_cid = int(row["pubchem_cid"])
                    if pubchem_cid in molecule_cache:
                        molecule_id = molecule_cache[pubchem_cid]
                    else:
                        molecule_id = conn.execute(
                            text(
                                """
                                INSERT INTO molecule (
                                    molecule_name, formula, exact_mass, pubchem_cid, chebi_id, hmdb_id, kegg_id, mesh_id, mesh_tree
                                )
                                VALUES (
                                    :molecule_name, :formula, :exact_mass, :pubchem_cid, :chebi_id, :hmdb_id, :kegg_id, :mesh_id, :mesh_tree
                                )
                                ON CONFLICT (pubchem_cid)
                                DO UPDATE SET
                                    molecule_name = EXCLUDED.molecule_name,
                                    formula = COALESCE(EXCLUDED.formula, molecule.formula),
                                    exact_mass = COALESCE(EXCLUDED.exact_mass, molecule.exact_mass),
                                    chebi_id = COALESCE(EXCLUDED.chebi_id, molecule.chebi_id),
                                    hmdb_id = COALESCE(EXCLUDED.hmdb_id, molecule.hmdb_id),
                                    kegg_id = COALESCE(EXCLUDED.kegg_id, molecule.kegg_id),
                                    mesh_id = COALESCE(EXCLUDED.mesh_id, molecule.mesh_id),
                                    mesh_tree = COALESCE(EXCLUDED.mesh_tree, molecule.mesh_tree)
                                RETURNING id_molecule
                                """
                            ),
                            {
                                "molecule_name": row.get("molecule_name"),
                                "formula": row.get("formula"),
                                "exact_mass": row.get("exact_mass"),
                                "pubchem_cid": pubchem_cid,
                                "chebi_id": row.get("chebi_id"),
                                "hmdb_id": row.get("hmdb_id"),
                                "kegg_id": row.get("kegg_id"),
                                "mesh_id": row.get("mesh_id"),
                                "mesh_tree": row.get("mesh_tree"),
                            },
                        ).scalar_one()
                        molecule_cache[pubchem_cid] = molecule_id

                candidate_id = conn.execute(
                    text(
                        """
                        INSERT INTO molecule_candidate (
                            id_signal, id_molecule, candidate_name,
                            fragmentation_score, base_score, isotopic_similarity
                        ) VALUES (
                            :id_signal, :id_molecule, :candidate_name,
                            :fragmentation_score, :base_score, :isotopic_similarity
                        )
                        RETURNING id_candidate
                        """
                    ),
                    {
                        "id_signal": db_signal_id,
                        "id_molecule": molecule_id,
                        "candidate_name": row.get("molecule_name"),
                        "fragmentation_score": row.get("fragmentation_score"),
                        "base_score": row.get("base_score"),
                        "isotopic_similarity": row.get("isotope_score"),
                    },
                ).scalar_one()

                conn.execute(
                    text(
                        """
                        INSERT INTO candidate_score (
                            id_candidate, frag_norm, base_norm, iso_norm, final_score
                        ) VALUES (
                            :id_candidate, :frag_norm, :base_norm, :iso_norm, :final_score
                        )
                        """
                    ),
                    {
                        "id_candidate": candidate_id,
                        "frag_norm": row.get("normalized_frag_score"),
                        "base_norm": row.get("normalized_base_score"),
                        "iso_norm": row.get("normalized_iso_score"),
                        "final_score": row.get("final_score"),
                    },
                )

                conn.execute(
                    text(
                        """
                        INSERT INTO candidate_probability (id_candidate, probability, ranking)
                        VALUES (:id_candidate, :probability, :ranking)
                        """
                    ),
                    {
                        "id_candidate": candidate_id,
                        "probability": row.get("probability"),
                        "ranking": int(row.get("ranking")) if pd.notna(row.get("ranking")) else None,
                    },
                )
