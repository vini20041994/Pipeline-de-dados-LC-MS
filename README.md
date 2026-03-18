# Pipeline de dados LC-MS (QuimioAnalytics)

Projeto de ETL para processar planilhas LC-MS, calcular ranking probabilístico Top 5 de candidatos moleculares, enriquecer metadados em bases públicas (PubChem, KEGG, ChEBI, HMDB e MeSH) e persistir os resultados em PostgreSQL.

## 1) Objetivo do projeto

Este repositório implementa um fluxo fim a fim para análises quimioinformáticas:

1. leitura de planilhas de identificação e abundância;
2. validação e transformação dos dados;
3. cálculo de score final e probabilidade posterior por candidato;
4. seleção de Top 5 por sinal analítico;
5. enriquecimento em bases externas;
6. carga no banco PostgreSQL para exploração analítica.

---

## 2) Estrutura do projeto

- `main.py`: orquestra o ETL ponta a ponta.
- `etl/`: módulos de extração, transformação, score, enriquecimento e carga.
- `config/database.py`: configuração de conexão com PostgreSQL.
- `database_schema_postgresql.sql`: DDL principal do schema.
- `docker-compose.yml`: serviços `postgres` e `adminer` (infra SQL).

Documentação de apoio:
- `ANALISE_PROJETO_QUIMIOANALYTICS.md`
- `ETL_PIPELINE_QUIMIOANALYTICS.md`
- `CALCULO_TOP5_MODELO.md`
- `MODELO_BANCO_QUIMIOANALYTICS.md`
- `ER_DIAGRAMA_QUIMIOANALYTICS.md`
- `SQL_CALCULO_TOP5_EXEMPLO.sql`

---

## 3) Pré-requisitos

- Python 3.10+
- Docker + Docker Compose
- Arquivos de entrada:
  - `data/identificacao.xlsx`
  - `data/abundancia.xlsx`

---

## 4) Passo a passo de execução (virtualenv + container SQL)

### 4.1 Criar e ativar ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.2 Subir banco PostgreSQL em container

```bash
docker compose up -d postgres pgadmin
```

pgAdmin (opcional): `http://localhost:5050`

### 4.3 Aplicar schema no PostgreSQL

```bash
docker exec -i quimioanalytics-db \
  psql -U postgres -d quimioanalytics \
  < database_schema_postgresql.sql
```

### 4.4 Executar o pipeline localmente (com virtualenv)

```bash
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=localhost
export DB_PORT=55432
export DB_NAME=quimioanalytics
export DB_SCHEMA=quimioanalytics

python main.py
```

### 4.5 Encerrar containers

```bash
docker compose down
```

---

## 5) Variáveis de ambiente

- `DB_USER` (default: `postgres`)
- `DB_PASSWORD` (default: `postgres`)
- `DB_HOST` (default: `localhost`)
- `DB_PORT` (default: `55432`)
- `DB_NAME` (default: `quimioanalytics`)
- `DB_SCHEMA` (default: `quimioanalytics`)

---

## 6) Fluxo técnico do pipeline

1. **Extract (`etl/extract.py`)**: leitura das planilhas de identificação e abundância.
2. **Transform (`etl/transform.py`)**: padronização, validação, `melt` e merge por `signal_id`.
3. **Score (`etl/score.py`)**: normalização, score final ponderado, posterior e ranking.
4. **Top 5**: recorte dos 5 melhores candidatos por sinal.
5. **Enrich (`etl/enrich.py`)**: enriquecimento via PubChem, KEGG, ChEBI, HMDB e MeSH.
6. **Load (`etl/load.py`)**: persistência transacional no PostgreSQL.

---

## 7) Troubleshooting

- **`docker: command not found`**: instale Docker Desktop/Engine com Compose.
- **Falha ao conectar no banco**: valide `DB_HOST`, `DB_PORT`, `DB_USER` e `DB_PASSWORD`.
  - Se estiver usando **pgAdmin** (http://localhost:5050), crie um servidor com:
    - **Hostname/address**: `postgres`
    - **Porta**: `5432`
    - **Maintenance DB**: `postgres`
    - **Username**: `postgres`
    - **Password**: `postgres`
    - **Save password**: habilitado (opcional)
- **Timeout em APIs externas**: tente novamente (enrichment depende de APIs públicas).
