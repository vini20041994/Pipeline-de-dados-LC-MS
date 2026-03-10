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

```python
import os
from pathlib import Path

RAW_DIR = "data/raw"

files = list(Path(RAW_DIR).glob("*"))

for f in files:
    print("Ingesting:", f)
```

## 4️⃣ Etapa 2 — Conversão de formato

Arquivos proprietários são convertidos para mzML.

### Ferramenta

ProteoWizard

### Exemplo

```bash
msconvert sample.raw --mzML --outdir data/mzml
```

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

### Exemplo de tabela

```text
feature_table.csv
```

## 6️⃣ Etapa 4 — Alinhamento e normalização

Alinha sinais entre amostras.

### Resultado

| feature | mz | rt | sample1 | sample2 |
|---|---:|---:|---:|---:|

## 7️⃣ Etapa 5 — Anotação de candidatos

Cada feature gera vários compostos possíveis.

### Consulta a bibliotecas

- espectros MS/MS
- massa exata
- isotopólogos

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

### Dados coletados

- taxonomia
- organismos onde o composto ocorre.
- ontologia química
- classe química (ex: flavonoid, alkaloid).
- aplicações
- uso farmacêutico, alimentar ou industrial.

### Exemplo de chamada API

```python
import requests

url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/caffeine/JSON"
response = requests.get(url)
data = response.json()
```

## 9️⃣ Etapa 7 — Sistema de pontuação

Score calculado usando múltiplos critérios.

### Exemplo

| critério | peso |
|---|---:|
| massa | 0.4 |
| fragmentação | 0.3 |
| taxonomia | 0.1 |
| ontologia | 0.1 |
| presença em bases | 0.1 |

### Fórmula

```text
score_total =
0.4*score_mass +
0.3*score_fragment +
0.1*score_taxonomy +
0.1*score_ontology +
0.1*score_database
```

## 🔟 Etapa 8 — Regra do Top 5

Seleciona apenas os 5 candidatos mais plausíveis.

### Exemplo em Python

```python
import pandas as pd

df = pd.read_csv("candidates.csv")

top5 = (
    df.sort_values("score_total", ascending=False)
      .groupby("feature_id")
      .head(5)
)
```

## 1️⃣1️⃣ Armazenamento em banco de dados

Estrutura recomendada.

### tabela features

```sql
CREATE TABLE features (
feature_id SERIAL PRIMARY KEY,
mz FLOAT,
retention_time FLOAT
);
```

### tabela candidatos

```sql
CREATE TABLE compound_candidates (
candidate_id SERIAL PRIMARY KEY,
feature_id INT,
compound_name TEXT,
pubchem_cid INT,
score_total FLOAT
);
```

### tabela metadados

```sql
CREATE TABLE compound_metadata (
compound_id INT,
taxonomy TEXT,
ontology_class TEXT,
industrial_use TEXT
);
```

## 1️⃣2️⃣ Orquestração do pipeline

Automação com Apache Airflow.

### Fluxo DAG

```text
ingest_raw_data
      │
convert_mzml
      │
feature_detection
      │
alignment
      │
candidate_annotation
      │
database_enrichment
      │
scoring
      │
top5_selection
```

## 1️⃣3️⃣ Estrutura de projeto

```text
lcms_project
│
├── data
│   ├── raw
│   ├── mzml
│   └── processed
│
├── pipelines
│   ├── ingestion.py
│   ├── feature_detection.py
│   ├── annotation.py
│   ├── enrichment.py
│   └── ranking.py
│
├── database
│   └── schema.sql
│
└── airflow
    └── lcms_dag.py
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
