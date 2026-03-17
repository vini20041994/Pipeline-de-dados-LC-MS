# Pipeline de dados LC-MS (QuimioAnalytics)

Projeto de ETL para processar planilhas LC-MS, calcular ranking probabilístico Top 5 de candidatos moleculares, enriquecer metadados em bases públicas (PubChem, KEGG, ChEBI, HMDB e MeSH) e persistir em PostgreSQL.

## 1) Objetivo do projeto

Este repositório implementa um fluxo de dados fim a fim para análises quimioinformáticas baseadas em LC-MS:

1. leitura de planilhas de identificação e abundância;
2. validação e transformação dos dados;
3. cálculo de score final e probabilidade posterior por candidato;
4. seleção dos Top 5 por sinal analítico;
5. enriquecimento em bases externas;
6. carga no banco PostgreSQL para exploração analítica.

---

## 2) Organização da documentação

### Documentação funcional e técnica
- [`ANALISE_PROJETO_QUIMIOANALYTICS.md`](ANALISE_PROJETO_QUIMIOANALYTICS.md): visão geral técnica e acadêmica do projeto.
- [`ETL_PIPELINE_QUIMIOANALYTICS.md`](ETL_PIPELINE_QUIMIOANALYTICS.md): explicação detalhada do fluxo ETL.
- [`CALCULO_TOP5_MODELO.md`](CALCULO_TOP5_MODELO.md): modelo matemático do cálculo de score e probabilidade.

### Banco de dados
- [`MODELO_BANCO_QUIMIOANALYTICS.md`](MODELO_BANCO_QUIMIOANALYTICS.md): modelagem conceitual/relacional.
- [`ER_DIAGRAMA_QUIMIOANALYTICS.md`](ER_DIAGRAMA_QUIMIOANALYTICS.md): diagrama ER em Mermaid.
- [`database_schema_postgresql.sql`](database_schema_postgresql.sql): DDL principal do schema.
- [`SQL_CALCULO_TOP5_EXEMPLO.sql`](SQL_CALCULO_TOP5_EXEMPLO.sql): exemplo de cálculo SQL para score e Top 5.

### Código e automação
- [`main.py`](main.py): orquestrador do pipeline ponta a ponta.
- [`etl/`](etl): módulos de extração, transformação, score, enriquecimento e carga.
- [`config/database.py`](config/database.py): configuração de conexão com PostgreSQL.
- [`scripts/run_pipeline.sh`](scripts/run_pipeline.sh): **único script geral** para setup e execução.
- [`docker-compose.yml`](docker-compose.yml): serviços `postgres` e `adminer`.

---

## 3) Pré-requisitos

1. Docker e Docker Compose instalados.
2. Python 3.10+ instalado (para execução local do ETL).
3. Cliente `psql` instalado (quando usar aplicação de schema via host).
4. Arquivos de entrada presentes:
   - `data/identificacao.xlsx`
   - `data/abundancia.xlsx`

---

## 4) Script único de execução (geral)

Para manter a operação simples, o projeto utiliza apenas **um script principal**:

```bash
bash scripts/run_pipeline.sh
```

### O que esse script faz, em detalhes

1. Lê variáveis de ambiente de banco e execução.
2. (Opcional) sobe os containers `postgres` e `adminer` com Docker Compose.
3. Valida interpretador Python e cria/usa `.venv`.
4. (Opcional) instala dependências do `requirements.txt`.
5. (Opcional) aplica `database_schema_postgresql.sql` usando `psql`.
6. Valida existência das planilhas de entrada.
7. Executa `main.py`.

---

## 5) Parâmetros do script geral

Todos os parâmetros abaixo podem ser passados por variável de ambiente:

- `DB_USER` (padrão: `postgres`)
- `DB_PASSWORD` (padrão: `postgres`)
- `DB_HOST` (padrão: `localhost`)
- `DB_PORT` (padrão: `55432`)
- `DB_NAME` (padrão: `quimioanalytics`)
- `DB_SCHEMA` (padrão: `quimioanalytics`)
- `COMPOSE_FILE` (padrão: `docker-compose.yml`)
- `START_DOCKER` (padrão: `1`) — sobe ou não os containers SQL.
- `INSTALL_DEPS` (padrão: `1`) — instala ou não dependências Python.
- `APPLY_SCHEMA` (padrão: `1`) — aplica ou não schema SQL.
- `PYTHON_CMD` (padrão: `python`) — interpretador base para criar venv.
- `VENV_DIR` (padrão: `.venv`) — diretório da virtualenv.
- `IDENT_FILE` (padrão: `data/identificacao.xlsx`) — entrada identificação.
- `ABUND_FILE` (padrão: `data/abundancia.xlsx`) — entrada abundância.

### Exemplos práticos

Execução completa (recomendada):
```bash
bash scripts/run_pipeline.sh
```

Executar ETL sem subir containers e sem reaplicar schema:
```bash
START_DOCKER=0 APPLY_SCHEMA=0 bash scripts/run_pipeline.sh
```

Executar sem reinstalar dependências:
```bash
INSTALL_DEPS=0 bash scripts/run_pipeline.sh
```

---

## 6) Fluxo técnico do pipeline (detalhado)

1. **Extract (`etl/extract.py`)**
   - lê planilhas Excel de identificação e abundância.
2. **Transform (`etl/transform.py`)**
   - padroniza nomes de colunas;
   - valida colunas mínimas obrigatórias;
   - converte abundância para formato longo por replicata;
   - mescla identificação e abundância por `signal_id`.
3. **Score (`etl/score.py`)**
   - normaliza scores de fragmentação/base/isótopo;
   - calcula `final_score` ponderado (`w1`, `w2`, `w3`);
   - estima prior, likelihood e posterior;
   - cria ranking por sinal.
4. **Top 5**
   - filtra os 5 melhores candidatos por sinal.
5. **Enrichment (`etl/enrich.py`)**
   - consulta PubChem, KEGG, ChEBI, HMDB e MeSH;
   - adiciona identificadores e metadados químicos ao dataset.
6. **Load (`etl/load.py`)**
   - persiste dados em modo transacional no PostgreSQL.

---

## 7) Descrição detalhada dos códigos e bibliotecas utilizadas

### `main.py`
- **Função no sistema:** orquestra todo o pipeline ponta a ponta (extract → transform → score → enrich → load).
- **Bibliotecas/módulos utilizados:**
  - `etl.extract`: leitura das planilhas de entrada;
  - `etl.transform`: validação e transformação dos dados;
  - `etl.score`: cálculo de score/probabilidade/ranking;
  - `etl.enrich`: enriquecimento em bases externas;
  - `etl.load`: persistência no PostgreSQL;
  - `config.database`: criação da engine SQLAlchemy.

### `etl/extract.py`
- **Função no sistema:** camada de extração dos arquivos Excel.
- **Bibliotecas utilizadas:**
  - `pandas`: `read_excel` para ingestão tabular;
  - `pathlib`: tipagem e manipulação de caminhos.

### `etl/transform.py`
- **Função no sistema:** limpeza de colunas, validação mínima, conversão para long format e merge.
- **Bibliotecas utilizadas:**
  - `pandas`: `dropna`, `melt`, `merge` e transformações tabulares.

### `etl/score.py`
- **Função no sistema:** cálculo matemático do score final e da probabilidade posterior; geração de ranking.
- **Bibliotecas utilizadas:**
  - `numpy`: operações numéricas vetorizadas (`zeros`, `where`, etc.);
  - `pandas`: agrupamento por sinal, transformação e ranking.

### `etl/enrich.py`
- **Função no sistema:** enriquecimento de candidatos moleculares via APIs públicas.
- **Bibliotecas utilizadas:**
  - `requests`: chamadas HTTP para PubChem, KEGG, OLS/ChEBI, HMDB e MeSH;
  - `tqdm`: barra de progresso no enriquecimento em lote;
  - `dataclasses`: modelagem do `EnrichmentRecord`;
  - `re`: extração de padrões textuais (ex.: identificadores HMDB).

### `etl/load.py`
- **Função no sistema:** carga transacional no banco relacional.
- **Bibliotecas utilizadas:**
  - `sqlalchemy` (`text`): SQL parametrizado para inserts/updates;
  - `pandas`: iteração e verificações de nulos no DataFrame.

### `config/database.py`
- **Função no sistema:** montagem da URL do banco e criação de engine com `search_path`.
- **Bibliotecas utilizadas:**
  - `os`: leitura de variáveis de ambiente;
  - `sqlalchemy`: criação de `Engine`.

### `scripts/run_pipeline.sh`
- **Função no sistema:** script geral único para operar todo o projeto.
- **Ferramentas utilizadas:**
  - `docker compose`: sobe `postgres` e `adminer`;
  - `python` + `venv` + `pip`: execução da aplicação Python;
  - `psql`: aplicação do schema SQL.

---

## 8) Acesso SQL (Adminer)

Quando `START_DOCKER=1`, o script sobe o Adminer automaticamente.

- URL: `http://localhost:8080`
- Sistema: `PostgreSQL`
- Servidor: `postgres`
- Usuário: `postgres`
- Senha: `postgres`
- Banco: `quimioanalytics`

---

## 9) Troubleshooting

- **`docker: command not found`**
  - instale Docker Desktop/Engine e Docker Compose;
  - ou execute com `START_DOCKER=0` se já tiver banco externo disponível.
- **`psql: command not found`**
  - instale cliente PostgreSQL no host;
  - ou execute com `APPLY_SCHEMA=0` se o schema já estiver aplicado.
- **Erro de conexão com banco**
  - valide `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`.
- **Timeout em APIs externas (enrichment)**
  - processo best-effort; campos podem ficar nulos sem interromper execução.
