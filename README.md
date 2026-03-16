# Pipeline-de-dados-LC-MS

Repositório com materiais de análise, modelagem de dados e implementação ETL do projeto **QuimioAnalytics**.

## Conteúdo

- [`ANALISE_PROJETO_QUIMIOANALYTICS.md`](ANALISE_PROJETO_QUIMIOANALYTICS.md): análise técnica e acadêmica consolidada do projeto.
- [`MODELO_BANCO_QUIMIOANALYTICS.md`](MODELO_BANCO_QUIMIOANALYTICS.md): arquitetura conceitual e diretrizes do banco para LC-MS.
- [`database_schema_postgresql.sql`](database_schema_postgresql.sql): DDL PostgreSQL com tabelas, constraints, índices e view `top5_candidates`.
- [`ER_DIAGRAMA_QUIMIOANALYTICS.md`](ER_DIAGRAMA_QUIMIOANALYTICS.md): diagrama ER (Mermaid) do banco PostgreSQL.
- [`CALCULO_TOP5_MODELO.md`](CALCULO_TOP5_MODELO.md): cálculo aplicado da regra probabilística e resultado Top 5.
- [`SQL_CALCULO_TOP5_EXEMPLO.sql`](SQL_CALCULO_TOP5_EXEMPLO.sql): cálculo SQL de score/probabilidade/ranking Top 5 sobre o schema.
- [`ETL_PIPELINE_QUIMIOANALYTICS.md`](ETL_PIPELINE_QUIMIOANALYTICS.md): guia do pipeline ETL em Python.
- [`main.py`](main.py): orquestração ponta a ponta do ETL.
- [`etl/`](etl): módulos de extração, transformação, score, enriquecimento e carga.
- [`config/database.py`](config/database.py): configuração de conexão com PostgreSQL.
- [`requirements.txt`](requirements.txt): dependências Python.


**Enriquecimento suportado no ETL:** KEGG, PubChem, ChEBI, HMDB e MeSH Tree.
