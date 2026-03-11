-- Relational schema for LC-MS pipeline outputs.

CREATE TABLE IF NOT EXISTS features (
    feature_id TEXT PRIMARY KEY,
    mz DOUBLE PRECISION NOT NULL,
    retention_time DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS compound_candidates (
    candidate_id BIGSERIAL PRIMARY KEY,
    feature_id TEXT NOT NULL REFERENCES features(feature_id),
    compound_name TEXT NOT NULL,
    score_raw DOUBLE PRECISION,
    score_norm DOUBLE PRECISION,
    rank INTEGER
);

CREATE TABLE IF NOT EXISTS compound_metadata (
    metadata_id BIGSERIAL PRIMARY KEY,
    feature_id TEXT NOT NULL REFERENCES features(feature_id),
    compound_name TEXT NOT NULL,
    taxonomy TEXT,
    organisms TEXT,
    ontology_class TEXT,
    chemical_class TEXT,
    applications TEXT,
    industrial_use TEXT,
    sources_found TEXT
);
