# Pipeline de Ingestão de Dados LC-MS

Um pipeline de ingestão de dados **LC-MS** (Liquid Chromatography–Mass Spectrometry) organiza todo o fluxo desde a geração dos espectros até a produção de dados estruturados para análise, anotação de compostos e integração com bases públicas.

## 1️⃣ Arquitetura geral do pipeline LC-MS

```text
LC-MS Instrument
       │
       ▼
Raw Data Acquisition
(.raw / .wiff / .d)
       │
       ▼
Conversão de formato
(mzML / mzXML)
       │
       ▼
Detecção de picos
(feature detection)
       │
       ▼
Alinhamento entre amostras
       │
       ▼
Anotação de candidatos
(libraries)
       │
       ▼
Enriquecimento de dados
(databases)
       │
       ▼
Ranking de plausibilidade
(Regra do Top 5)
       │
       ▼
Banco de dados científico
```

## 2️⃣ Etapa 1 — Aquisição de dados

O instrumento LC-MS gera arquivos proprietários.

### Formatos comuns

| Fabricante | Formato |
|---|---|
| Thermo | `.raw` |
| Agilent | `.d` |
| Sciex | `.wiff` |
| Waters | `.raw` |

Esses arquivos contêm, tipicamente:

- espectro de massa;
- intensidade;
- tempo de retenção;
- fragmentação MS/MS.

## 3️⃣ Etapa 2 — Conversão de formato

Os dados são convertidos para formatos abertos.

### Ferramenta principal

- **ProteoWizard**

### Formatos de saída

| Formato | Uso |
|---|---|
| `mzML` | padrão atual |
| `mzXML` | legado |
| `mgf` | espectros MS/MS |

### Exemplo

```bash
msconvert sample.raw --mzML
```

## 4️⃣ Etapa 3 — Detecção de features

Identificação de picos cromatográficos.

### Ferramentas comuns

- **MZmine**
- **XCMS**
- **Progenesis QI**

### Exemplo de resultado

| Feature | m/z | RT | Intensidade |
|---|---:|---:|---:|
| F1 | 301.216 | 4.3 | 234000 |
| F2 | 195.087 | 6.7 | 120000 |

## 5️⃣ Etapa 4 — Alinhamento de amostras

Corrige variações entre corridas cromatográficas.

### Resultado esperado

```text
Sample 1
Sample 2
Sample 3
        │
        ▼
Aligned Feature Table
```

### Tabela final

| Feature | m/z | RT | Sample1 | Sample2 | Sample3 |
|---|---:|---:|---:|---:|---:|

## 6️⃣ Etapa 5 — Anotação de candidatos

Cada feature gera vários compostos possíveis.

### Consulta em bibliotecas

- espectros MS/MS;
- massa exata;
- isotopólogos.

### Fontes

- PubChem
- ChEBI
- Human Metabolome Database (HMDB)
- FooDB

### Exemplo

| Feature | Candidate | Score |
|---|---|---:|
| F1 | Compound A | 0.89 |
| F1 | Compound B | 0.82 |
| F1 | Compound C | 0.74 |

## 7️⃣ Etapa 6 — Enriquecimento de dados

Cada candidato recebe metadados adicionais.

### Taxonomia

Organismos onde ocorre.

| Compound | Organism |
|---|---|
| Quercetin | plantas |
| Caffeine | Coffea |

### Ontologia química

Obtida via ChEBI ou MeSH Tree.

| Compound | Class |
|---|---|
| Quercetin | flavonoid |
| Caffeine | alkaloid |

### Aplicações

Extraídas de PubChem.

| Compound | Use |
|---|---|
| Citric acid | food additive |
| Acetone | solvent |

## 8️⃣ Etapa 7 — Sistema de pontuação

Score calculado com múltiplos critérios:

```text
Score_total =
mass_accuracy +
fragmentation +
taxonomy +
ontology +
database_presence
```

## 9️⃣ Etapa 8 — Regra do Top 5

Após ranking:

```text
Candidate ranking
      │
      ▼
Top 5 compostos
```

Somente esses seguem para validação manual.

## 🔟 Estrutura de banco de dados

### Tabela de features

```text
features
-------
feature_id
mz
retention_time
intensity
```

### Tabela de candidatos

```text
compound_candidates
-------
feature_id
compound_name
pubchem_cid
chebi_id
score
```

### Tabela de metadados

```text
compound_metadata
-------
compound_id
taxonomy
ontology_class
industrial_use
```

## 1️⃣1️⃣ Pipeline automatizado

Arquitetura moderna:

```text
LC-MS
 │
 ▼
Data Lake
 │
 ▼
ETL Pipeline
 │
 ▼
Feature Detection
 │
 ▼
Candidate Annotation
 │
 ▼
Database Enrichment
 │
 ▼
Top 5 Ranking
 │
 ▼
Scientific Database
```

### Ferramentas recomendadas

| Tipo | Tecnologia |
|---|---|
| ETL | Python |
| Orquestração | Apache Airflow |
| Processamento | Apache Spark |
| Banco | PostgreSQL |
| Grafos | Neo4j |

## 1️⃣2️⃣ Estrutura ideal de projeto

```text
lcms_pipeline
│
├── ingestion
├── preprocessing
├── feature_detection
├── annotation
├── enrichment
├── ranking
└── database
```
