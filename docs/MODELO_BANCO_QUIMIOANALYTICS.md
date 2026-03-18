# Modelo de Banco de Dados — QuimioAnalytics (PostgreSQL)

Este documento consolida um modelo relacional para suportar o pipeline LC-MS com foco em:

- armazenamento de sinais analíticos;
- registro de candidatos moleculares por sinal;
- persistência de scores instrumentais/probabilísticos;
- enriquecimento com metadados de APIs científicas;
- suporte a replicatas dinâmicas.

## 1) Arquitetura conceitual

```text
experiment
   │
   └── sample
          │
          └── analytical_signal
                 │
                 └── molecule_candidate
                        │
                        ├── candidate_score
                        ├── candidate_probability
                        └── molecule (metadados)
                               ├── molecule_taxonomy
                               ├── molecule_ontology
                               └── molecule_application
```

## 2) Rastreabilidade científica

O desenho assegura a trilha completa:

**Experimento → Amostra → Sinal → Candidato → Score/Probabilidade → Enriquecimento**.

## 3) Regras principais de modelagem

- Um experimento possui várias amostras.
- Uma amostra possui vários sinais analíticos.
- Um sinal possui N replicatas e N candidatos.
- Cada candidato possui score instrumental e probabilidade/ranking.
- Uma molécula enriquecida pode ser referenciada por múltiplos candidatos.

## 4) Estratégia de carga ETL

```text
Excel Identificação/Abundância
          ↓
Python (Pandas)
          ↓
analytical_signal + signal_replicate
          ↓
molecule_candidate
          ↓
candidate_score + candidate_probability
          ↓
APIs científicas (PubChem/KEGG/HMDB/ChEBI)
          ↓
molecule + tabelas de enriquecimento
```

## 5) Consumo em BI

A view `top5_candidates` simplifica o dashboard para exibir, por sinal:

- Top 5 candidatos;
- score final;
- ranking;
- identificadores da molécula enriquecida.

## 6) Benefícios

- Suporte a replicatas variáveis por sinal.
- Separação entre **candidato** (hipótese) e **molécula** (entidade enriquecida).
- Boa aderência a ETL incremental.
- Modelo pronto para auditoria e rastreabilidade.

## 7) Diagrama ER

O diagrama ER completo está em [`ER_DIAGRAMA_QUIMIOANALYTICS.md`](ER_DIAGRAMA_QUIMIOANALYTICS.md), em formato Mermaid para facilitar edição e versionamento.
