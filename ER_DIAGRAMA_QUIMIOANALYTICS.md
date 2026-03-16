# Diagrama ER — QuimioAnalytics

Abaixo está o diagrama entidade-relacionamento do banco PostgreSQL do projeto.

```mermaid
erDiagram
    experiment ||--o{ sample : has
    sample ||--o{ analytical_signal : has
    analytical_signal ||--o{ signal_replicate : has
    analytical_signal ||--o{ molecule_candidate : generates

    molecule ||--o{ molecule_candidate : enriches
    molecule ||--o{ molecule_taxonomy : has
    molecule ||--o{ molecule_ontology : has
    molecule ||--o{ molecule_application : has

    molecule_candidate ||--|| candidate_score : scored_by
    molecule_candidate ||--|| candidate_probability : ranked_by

    experiment {
      bigint id_experiment PK
      varchar experiment_name
      varchar instrument
      timestamp created_at
    }

    sample {
      bigint id_sample PK
      bigint id_experiment FK
      varchar sample_code
      varchar matrix_type
      timestamp created_at
    }

    analytical_signal {
      bigint id_signal PK
      bigint id_sample FK
      numeric mz
      numeric retention_time
      numeric intensity
      varchar signal_key
      timestamp created_at
    }

    signal_replicate {
      bigint id_replicate PK
      bigint id_signal FK
      int replicate_number
      numeric abundance
    }

    molecule {
      bigint id_molecule PK
      varchar molecule_name
      varchar formula
      numeric exact_mass
      bigint pubchem_cid
      varchar chebi_id
      varchar hmdb_id
      varchar kegg_id
      varchar mesh_id
      varchar mesh_tree
      timestamp created_at
    }

    molecule_candidate {
      bigint id_candidate PK
      bigint id_signal FK
      bigint id_molecule FK
      varchar candidate_name
      numeric fragmentation_score
      numeric base_score
      numeric isotopic_similarity
    }

    candidate_score {
      bigint id_score PK
      bigint id_candidate FK
      numeric frag_norm
      numeric base_norm
      numeric iso_norm
      numeric final_score
    }

    candidate_probability {
      bigint id_probability PK
      bigint id_candidate FK
      numeric probability
      int ranking
    }

    molecule_taxonomy {
      bigint id_taxonomy PK
      bigint id_molecule FK
      varchar kingdom
      varchar phylum
      varchar class
      varchar family
      varchar genus
      varchar species
    }

    molecule_ontology {
      bigint id_ontology PK
      bigint id_molecule FK
      varchar ontology_source
      varchar ontology_term
      varchar ontology_id
    }

    molecule_application {
      bigint id_application PK
      bigint id_molecule FK
      varchar application_type
      text description
      varchar source_database
    }
```

## Leitura rápida

- **Rastreabilidade**: `experiment` → `sample` → `analytical_signal` → `molecule_candidate`.
- **Replicatas dinâmicas**: `signal_replicate` permite N replicatas por sinal.
- **Top 5**: `candidate_probability.ranking` suporta seleção para dashboard.
- **Enriquecimento científico**: `molecule` e tabelas filhas armazenam taxonomia, ontologia e aplicações.
