-- =====================================================
-- QUIMIOANALYTICS DATABASE SCHEMA
-- =====================================================

CREATE SCHEMA IF NOT EXISTS quimioanalytics;

SET search_path TO quimioanalytics;

-- =====================================================
-- TABELA EXPERIMENT
-- =====================================================

CREATE TABLE IF NOT EXISTS experiment (
    id_experiment SERIAL PRIMARY KEY,
    experiment_name VARCHAR(200) NOT NULL,
    instrument VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- TABELA SAMPLE
-- =====================================================

CREATE TABLE IF NOT EXISTS sample (
    id_sample SERIAL PRIMARY KEY,
    id_experiment INTEGER NOT NULL,
    sample_code VARCHAR(100) NOT NULL,
    matrix_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sample_experiment
    FOREIGN KEY (id_experiment)
    REFERENCES experiment(id_experiment)
    ON DELETE CASCADE
);

-- =====================================================
-- TABELA ANALYTICAL SIGNAL
-- =====================================================

CREATE TABLE IF NOT EXISTS analytical_signal (
    id_signal SERIAL PRIMARY KEY,
    id_sample INTEGER NOT NULL,

    signal_key VARCHAR(100),

    mz NUMERIC(12,6),
    retention_time NUMERIC(10,4),
    intensity NUMERIC,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_signal_sample
    FOREIGN KEY (id_sample)
    REFERENCES sample(id_sample)
    ON DELETE CASCADE
);

-- =====================================================
-- TABELA REPLICATAS DE ABUNDÂNCIA
-- =====================================================

CREATE TABLE IF NOT EXISTS signal_replicate (
    id_replicate SERIAL PRIMARY KEY,
    id_signal INTEGER NOT NULL,

    replicate_number INTEGER NOT NULL,
    abundance NUMERIC,

    CONSTRAINT fk_replicate_signal
    FOREIGN KEY (id_signal)
    REFERENCES analytical_signal(id_signal)
    ON DELETE CASCADE
);

-- =====================================================
-- TABELA MOLECULE
-- =====================================================

CREATE TABLE IF NOT EXISTS molecule (
    id_molecule SERIAL PRIMARY KEY,

    molecule_name VARCHAR(200) NOT NULL,
    formula VARCHAR(100),
    exact_mass NUMERIC,

    pubchem_cid INTEGER UNIQUE,
    chebi_id VARCHAR(50),
    hmdb_id VARCHAR(50),
    kegg_id VARCHAR(50),
    mesh_id VARCHAR(50),
    mesh_tree VARCHAR(120),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- TAXONOMIA BIOLÓGICA
-- =====================================================

CREATE TABLE IF NOT EXISTS molecule_taxonomy (
    id_taxonomy SERIAL PRIMARY KEY,
    id_molecule INTEGER NOT NULL,

    kingdom VARCHAR(100),
    phylum VARCHAR(100),
    class VARCHAR(100),
    family VARCHAR(100),
    genus VARCHAR(100),
    species VARCHAR(100),

    CONSTRAINT fk_taxonomy_molecule
    FOREIGN KEY (id_molecule)
    REFERENCES molecule(id_molecule)
    ON DELETE CASCADE
);

-- =====================================================
-- ONTOLOGIA QUÍMICA
-- =====================================================

CREATE TABLE IF NOT EXISTS molecule_ontology (
    id_ontology SERIAL PRIMARY KEY,
    id_molecule INTEGER NOT NULL,

    ontology_source VARCHAR(100),
    ontology_term VARCHAR(200),
    ontology_id VARCHAR(100),

    CONSTRAINT fk_ontology_molecule
    FOREIGN KEY (id_molecule)
    REFERENCES molecule(id_molecule)
    ON DELETE CASCADE
);

-- =====================================================
-- APLICAÇÕES DA MOLÉCULA
-- =====================================================

CREATE TABLE IF NOT EXISTS molecule_application (
    id_application SERIAL PRIMARY KEY,
    id_molecule INTEGER NOT NULL,

    application_type VARCHAR(200),
    description TEXT,
    source_database VARCHAR(100),

    CONSTRAINT fk_application_molecule
    FOREIGN KEY (id_molecule)
    REFERENCES molecule(id_molecule)
    ON DELETE CASCADE
);

-- =====================================================
-- CANDIDATOS A MOLÉCULA
-- =====================================================

CREATE TABLE IF NOT EXISTS molecule_candidate (
    id_candidate SERIAL PRIMARY KEY,
    id_signal INTEGER NOT NULL,
    id_molecule INTEGER,

    candidate_name VARCHAR(200),

    fragmentation_score NUMERIC,
    base_score NUMERIC,
    isotopic_similarity NUMERIC,

    CONSTRAINT fk_candidate_signal
    FOREIGN KEY (id_signal)
    REFERENCES analytical_signal(id_signal)
    ON DELETE CASCADE,

    CONSTRAINT fk_candidate_molecule
    FOREIGN KEY (id_molecule)
    REFERENCES molecule(id_molecule)
);

-- =====================================================
-- SCORE NORMALIZADO
-- =====================================================

CREATE TABLE IF NOT EXISTS candidate_score (
    id_score SERIAL PRIMARY KEY,
    id_candidate INTEGER NOT NULL,

    frag_norm NUMERIC,
    base_norm NUMERIC,
    iso_norm NUMERIC,

    final_score NUMERIC,

    CONSTRAINT fk_score_candidate
    FOREIGN KEY (id_candidate)
    REFERENCES molecule_candidate(id_candidate)
    ON DELETE CASCADE
);

-- =====================================================
-- PROBABILIDADE FINAL
-- =====================================================

CREATE TABLE IF NOT EXISTS candidate_probability (
    id_probability SERIAL PRIMARY KEY,
    id_candidate INTEGER NOT NULL,

    probability NUMERIC,
    ranking INTEGER,

    CONSTRAINT fk_probability_candidate
    FOREIGN KEY (id_candidate)
    REFERENCES molecule_candidate(id_candidate)
    ON DELETE CASCADE
);

-- =====================================================
-- ÍNDICES PARA PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_signal_sample
ON analytical_signal(id_sample);

CREATE INDEX IF NOT EXISTS idx_candidate_signal
ON molecule_candidate(id_signal);

CREATE INDEX IF NOT EXISTS idx_candidate_score
ON candidate_score(id_candidate);

CREATE INDEX IF NOT EXISTS idx_probability_candidate
ON candidate_probability(id_candidate);

-- =====================================================
-- VIEW TOP 5
-- =====================================================

CREATE OR REPLACE VIEW top5_candidates AS
SELECT
    s.id_signal,
    COALESCE(m.molecule_name, mc.candidate_name) AS molecule_name,
    cs.final_score,
    cp.probability,
    cp.ranking
FROM candidate_probability cp
JOIN molecule_candidate mc
ON cp.id_candidate = mc.id_candidate
JOIN analytical_signal s
ON mc.id_signal = s.id_signal
LEFT JOIN molecule m
ON mc.id_molecule = m.id_molecule
LEFT JOIN candidate_score cs
ON cs.id_candidate = mc.id_candidate
WHERE cp.ranking <= 5
ORDER BY s.id_signal, cp.ranking;
