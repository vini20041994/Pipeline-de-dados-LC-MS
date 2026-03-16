-- =====================================================
-- CÁLCULO TOP 5 UTILIZANDO A MODELAGEM DO SCHEMA
-- =====================================================
-- Pré-condição: candidate_score e candidate_probability vazias para os candidatos alvo.
-- Escopo: calcula para todos os candidatos já inseridos em molecule_candidate.

SET search_path TO quimioanalytics;

WITH norm AS (
    SELECT
        mc.id_candidate,
        mc.id_signal,
        mc.fragmentation_score,
        mc.base_score,
        mc.isotopic_similarity,

        CASE
            WHEN MAX(mc.fragmentation_score) OVER (PARTITION BY mc.id_signal)
               = MIN(mc.fragmentation_score) OVER (PARTITION BY mc.id_signal)
            THEN 0
            ELSE (mc.fragmentation_score - MIN(mc.fragmentation_score) OVER (PARTITION BY mc.id_signal))
                 / NULLIF(
                     MAX(mc.fragmentation_score) OVER (PARTITION BY mc.id_signal)
                     - MIN(mc.fragmentation_score) OVER (PARTITION BY mc.id_signal),
                     0
                 )
        END AS frag_norm,

        CASE
            WHEN MAX(mc.base_score) OVER (PARTITION BY mc.id_signal)
               = MIN(mc.base_score) OVER (PARTITION BY mc.id_signal)
            THEN 0
            ELSE (mc.base_score - MIN(mc.base_score) OVER (PARTITION BY mc.id_signal))
                 / NULLIF(
                     MAX(mc.base_score) OVER (PARTITION BY mc.id_signal)
                     - MIN(mc.base_score) OVER (PARTITION BY mc.id_signal),
                     0
                 )
        END AS base_norm,

        CASE
            WHEN MAX(mc.isotopic_similarity) OVER (PARTITION BY mc.id_signal)
               = MIN(mc.isotopic_similarity) OVER (PARTITION BY mc.id_signal)
            THEN 0
            ELSE (mc.isotopic_similarity - MIN(mc.isotopic_similarity) OVER (PARTITION BY mc.id_signal))
                 / NULLIF(
                     MAX(mc.isotopic_similarity) OVER (PARTITION BY mc.id_signal)
                     - MIN(mc.isotopic_similarity) OVER (PARTITION BY mc.id_signal),
                     0
                 )
        END AS iso_norm

    FROM molecule_candidate mc
), score_base AS (
    SELECT
        n.*,
        ((n.frag_norm * 0.4) + (n.base_norm * 0.4) + (n.iso_norm * 0.2)) AS final_score,
        (n.base_norm + 1e-9)
            / NULLIF(SUM(n.base_norm + 1e-9) OVER (PARTITION BY n.id_signal), 0) AS prior_probability,
        (n.frag_norm + 1e-9) * (n.base_norm + 1e-9) * (n.iso_norm + 1e-9) AS likelihood
    FROM norm n
), posterior AS (
    SELECT
        sb.*,
        (sb.likelihood * sb.prior_probability)
            / NULLIF(SUM(sb.likelihood * sb.prior_probability) OVER (PARTITION BY sb.id_signal), 0) AS probability
    FROM score_base sb
)
INSERT INTO candidate_score (id_candidate, frag_norm, base_norm, iso_norm, final_score)
SELECT p.id_candidate, p.frag_norm, p.base_norm, p.iso_norm, p.final_score
FROM posterior p
ON CONFLICT DO NOTHING;

INSERT INTO candidate_probability (id_candidate, probability, ranking)
SELECT
    p.id_candidate,
    p.probability,
    RANK() OVER (PARTITION BY p.id_signal ORDER BY p.final_score DESC) AS ranking
FROM posterior p
ON CONFLICT DO NOTHING;

-- Consulta final do Top 5 por sinal
SELECT *
FROM top5_candidates
ORDER BY id_signal, ranking;
