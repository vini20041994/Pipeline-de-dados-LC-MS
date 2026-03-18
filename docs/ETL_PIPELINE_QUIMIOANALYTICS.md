# Pipeline ETL — QuimioAnalytics

Implementação de referência de um ETL Python integrado ao schema PostgreSQL do projeto.

## Etapas automatizadas

1. Leitura de planilhas Excel (`Identificação` e `Abundância`).
2. Limpeza e normalização dos dados.
3. Transformação da abundância (`melt`) para suportar replicatas dinâmicas.
4. Cálculo de score final e probabilidade por sinal.
5. Seleção de Top 5 por sinal.
6. Enriquecimento de metadados via APIs: PubChem, KEGG, ChEBI, HMDB e MeSH Tree.
7. Persistência em PostgreSQL com SQLAlchemy.

## Estrutura criada

```text
config/
  database.py
etl/
  extract.py
  transform.py
  score.py
  enrich.py
  load.py
main.py
requirements.txt
```

## Pré-requisitos

- Banco PostgreSQL com schema aplicado (`../sql/database_schema_postgresql.sql`) (inclui `CREATE SCHEMA quimioanalytics` e `SET search_path`).
- Arquivos Excel em `data/identificacao.xlsx` e `data/abundancia.xlsx`.

## Variáveis de ambiente

- `DB_USER` (default: `postgres`)
- `DB_PASSWORD` (default: `postgres`)
- `DB_HOST` (default: `localhost`)
- `DB_PORT` (default: `5432`)
- `DB_NAME` (default: `quimioanalytics`)
- `DB_SCHEMA` (default: `quimioanalytics`)

## Execução

```bash
# local (virtualenv)
pip install -r requirements.txt
python main.py
```

## Colunas esperadas

### Identificação

- `sample_code`
- `signal_id`
- `signal_key`
- `mz`
- `retention_time`
- `intensity`
- `molecule_name`
- `fragmentation_score`
- `base_score`
- `isotope_score`
- `matrix_type` (opcional)

### Abundância

- `signal_id`
- colunas de replicata (ex: `replicate_1`, `replicate_2`, `replicate_3`)

## Observações

- A etapa de enriquecimento usa cache em memória por execução para reduzir chamadas repetidas.
- Bases consultadas no enriquecimento: **PubChem, KEGG, ChEBI, HMDB e MeSH Tree**.
- O loader cria experimento, amostras, sinais, replicatas, candidatos, scores e probabilidades.
- A tabela `molecule` é alimentada por `pubchem_cid` com `upsert`.

## Modelagem matemática aplicada

A etapa de score aplica a regra descrita no projeto:

- `final_score = w1*frag_norm + w2*base_norm + w3*iso_norm`
- `posterior_probability` via Bayes por sinal (`signal_id`)
- `ranking` por `final_score` e recorte em `Top 5`

Exemplo calculado: [`CALCULO_TOP5_MODELO.md`](CALCULO_TOP5_MODELO.md).
