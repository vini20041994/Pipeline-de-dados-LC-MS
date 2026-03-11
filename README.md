# Pipeline de Ingestão de Dados LC-MS

Um pipeline de dados **LC-MS** (Liquid Chromatography–Mass Spectrometry) organiza o fluxo desde os arquivos brutos até a geração de candidatos anotados, enriquecidos e ranqueados para análise científica.

## 1️⃣ Visão geral do pipeline

```text
LC-MS Instrument
      │
      ▼
1. Data Ingestion
      │
      ▼
2. Format Conversion
      │
      ▼
3. Feature Detection
      │
      ▼
4. Alignment & Normalization
      │
      ▼
5. Candidate Annotation
      │
      ▼
6. Database Enrichment
      │
      ▼
7. Scoring System
      │
      ▼
8. Top 5 Rule
      │
      ▼
9. Storage & Visualization
```

## 2️⃣ Arquitetura tecnológica

Arquitetura moderna de ciência de dados:

```text
LC-MS data
   │
   ▼
Data Lake (raw spectra)
   │
   ▼
ETL Pipeline
   │
   ▼
Feature extraction
   │
   ▼
Chemical annotation
   │
   ▼
Knowledge enrichment
   │
   ▼
Ranking engine
   │
   ▼
Database + Dashboard
```

### Tecnologias recomendadas

| Função | Ferramenta |
|---|---|
| ingestão | Python |
| orquestração | Apache Airflow |
| processamento distribuído | Apache Spark |
| banco relacional | PostgreSQL |
| banco de grafos | Neo4j |
| containerização | Docker |

## 3️⃣ Etapa 1 — Ingestão de dados

### Entrada

arquivos gerados pelo LC-MS.

### Exemplo

```text
data/raw/
  sample1.raw
  sample2.raw
  sample3.raw
```

### Script de ingestão

```bash
python -m lcms_project.pipelines.ingestion \
  --raw-dir data/raw \
  --output data/processed/ingestion_manifest.json
```

O manifesto de ingestão inclui `sample_id`, caminho completo, tamanho em bytes,
hash SHA-256 e timestamp UTC para rastreabilidade.

> **Importante:** a ingestão **não** converte automaticamente os arquivos para mzML.

## 4️⃣ Etapa 2 — Conversão de formato

Arquivos proprietários são convertidos para mzML.

### Ferramenta

ProteoWizard

### Exemplo

```bash
python -m lcms_project.pipelines.conversion \
  --input-dir data/raw \
  --output-dir data/mzml \
  --report data/processed/conversion_report.json
```

Use `--dry-run` para validar descoberta e geração de relatório sem executar o `msconvert`.

### Saída

```text
data/mzml/sample1.mzML
```

## 5️⃣ Etapa 3 — Detecção de features

Detecção de picos cromatográficos.

### Ferramentas

- MZmine
- XCMS

### Resultado

```text
feature	m/z	RT	intensity
```

### Execução da etapa

```bash
python -m lcms_project.pipelines.feature_detection \
  --input data/mzml/points.csv \
  --output data/processed/feature_table.csv
```

Entrada esperada (CSV): colunas `mz`, `rt`, `intensity`.

### Exemplo de tabela

```text
feature_table.csv
```

## 6️⃣ Etapa 4 — Alinhamento e normalização

Alinha sinais entre amostras e normaliza intensidades por TIC (Total Ion Current),
escalando cada amostra para a mediana global.

### Execução da etapa

```bash
python -m lcms_project.pipelines.alignment_normalization \
  --input data/processed/sample_features.csv \
  --output-long data/processed/aligned_features_long.csv \
  --output-matrix data/processed/aligned_feature_matrix.csv
```

Entrada esperada (CSV): colunas `sample_id`, `mz`, `rt`, `intensity`.

### Resultado

| aligned_feature_id | mz | rt | sample1 | sample2 |
|---|---:|---:|---:|---:|

## 7️⃣ Etapa 5 — Anotação de candidatos

Cada feature gera vários compostos possíveis.

### Consulta a bibliotecas

- espectros MS/MS
- massa exata
- isotopólogos

### Execução da etapa

```bash
python -m lcms_project.pipelines.annotation \
  --features data/processed/feature_table.csv \
  --library data/reference/compound_library.csv \
  --output data/processed/candidates.csv
```

Entrada esperada:
- features CSV com colunas `feature_id`, `mz`, `rt`
- biblioteca CSV com colunas `compound_name`, `exact_mass`, `formula`, `source`

O script calcula erro de massa em ppm, atribui `score_mass` e retorna até `top-k` candidatos por feature.

### Exemplo

```text
feature	compound	score
```

## 8️⃣ Etapa 6 — Enriquecimento com bases públicas

Para cada composto candidato, o pipeline consulta:

- PubChem
- ChEBI
- Human Metabolome Database
- FooDB

### Execução da etapa

```bash
python -m lcms_project.pipelines.enrichment \
  --candidates data/processed/candidates.csv \
  --output data/processed/enriched_candidates.csv \
  --capabilities-output data/processed/enrichment_source_capabilities.csv
```

Use `--dry-run` para validar o fluxo sem chamadas HTTP externas.

### Dados coletados

- identificadores por base (`pubchem_cid`, `chebi_id`, `hmdb_id`, `foodb_id`)
- metadados básicos (`pubchem_title`)
- campos de enriquecimento para taxonomia, ontologia, classe química e aplicações
- fontes com ocorrência encontrada em `sources_found`

### Verificação das fontes para dados coletados

O pipeline gera `enrichment_source_capabilities.csv` com a checagem de cobertura das fontes para:
- taxonomia
- organismos de ocorrência
- ontologia química
- classe química
- aplicações
- uso farmacêutico/alimentar/industrial

## 9️⃣ Etapa 7 — Sistema de pontuação

Objetivo: estimar a probabilidade de cada candidato ser o verdadeiro composto,
combinando evidências espectrais e biológicas no modelo Bayesiano.

### Execução da etapa

```bash
python -m lcms_project.pipelines.ranking \
  --input data/processed/enriched_candidates.csv \
  --output data/processed/scored_candidates.csv \
  --top-output data/processed/top5_candidates.csv \
  --sigma-ppm 5 \
  --alpha-msms 1.2
```

### Modelo matemático executado

Probabilidade posterior por candidato:

```text
P(C_i|D) = [P(D|C_i) * P(C_i)] / P(D)
```

Decomposição da evidência:

```text
P(D|C_i) = P_mass * P_msms * P_isotope
```

Termos implementados no script:

```text
error_ppm = ((m_obs - m_theo) / m_theo) * 10^6
P_mass = exp(-|error_ppm| / sigma)
P_msms = cosine^alpha
P_isotope = isotope_similarity   (ou 1 - |isotope_delta|)
P(C_i) = w_db*DB + w_taxonomy*Taxonomy + w_ontology*Ontology
Score_raw = P_mass * P_msms * P_isotope * P(C_i)
Score_norm = Score_raw / sum_j(Score_raw_j)   # por feature
```

Critérios biológicos no prior `P(C_i)`:
- DB: presença em múltiplas bases (PubChem, ChEBI, HMDB, FooDB)
- Taxonomy: ocorrência taxonômica/organismos compatíveis
- Ontology: classe química/ontologia plausível para a matriz

## 🔟 Etapa 8 — Regra do Top 5

Seleciona apenas os 5 candidatos mais plausíveis.

### Exemplo em Python

```python
import pandas as pd

df = pd.read_csv("candidates.csv")

top5 = (
    df.sort_values("score_norm", ascending=False)
      .groupby("feature_id")
      .head(5)
)
```

## 1️⃣1️⃣ Armazenamento em banco de dados

A etapa de armazenamento persiste resultados de ranking e enriquecimento em banco relacional.

### Execução da etapa

```bash
python -m lcms_project.pipelines.storage \
  --db data/warehouse/lcms.db \
  --scored data/processed/scored_candidates.csv \
  --enriched data/processed/enriched_candidates.csv
```

### Esquema lógico (PostgreSQL)

Arquivo: `lcms_project/database/schema.sql`

- `features(feature_id, mz, retention_time)`
- `compound_candidates(feature_id, compound_name, score_raw, score_norm, rank)`
- `compound_metadata(feature_id, compound_name, taxonomy, organisms, ontology_class, chemical_class, applications, industrial_use, sources_found)`

A implementação da pipeline usa SQLite para execução local e segue o mesmo modelo relacional.


## 1️⃣2️⃣ Execução única do pipeline

A orquestração em Airflow foi removida e substituída por um script único de execução fim a fim.

### Script único

```bash
./run_pipeline.sh \
  --raw-dir data/raw \
  --mzml-dir data/mzml \
  --processed-dir data/processed \
  --reference-library data/reference/compound_library.csv \
  --db-path data/warehouse/lcms.db
```

Opções úteis:
- `--dry-run-conversion` para não chamar `msconvert`
- `--dry-run-enrichment` para não chamar APIs externas
- `--help` para listar todos os parâmetros


## 1️⃣3️⃣ Estrutura de projeto

```text
.
├── run_pipeline.sh
├── README.md
└── lcms_project
    ├── data
    │   ├── raw
    │   ├── mzml
    │   └── processed
    ├── pipelines
    │   ├── ingestion.py
    │   ├── conversion.py
    │   ├── feature_detection.py
    │   ├── alignment_normalization.py
    │   ├── annotation.py
    │   ├── enrichment.py
    │   ├── ranking.py
    │   └── storage.py
    └── database
        └── schema.sql
```

## 1️⃣4️⃣ Resultado final

O pipeline produz:

- tabela de features
- sinais detectados
- tabela de candidatos
- compostos possíveis
- ranking
- Top 5 candidatos por sinal
- metadados científicos
- taxonomia
- ontologia
- aplicações
