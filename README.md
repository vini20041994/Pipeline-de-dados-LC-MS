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
- [`scripts/`](scripts): scripts utilitários para subir stack SQL, aplicar schema e executar ETL.
- [`docker-compose.yml`](docker-compose.yml): serviços de banco e cliente SQL web.

---

## 3) Pré-requisitos

1. Docker e Docker Compose instalados.
2. Python 3.10+ instalado (para execução local do ETL).
3. Cliente `psql` instalado (quando usar aplicação de schema via host).
4. Arquivos de entrada presentes:
   - `data/identificacao.xlsx`
   - `data/abundancia.xlsx`

---

## 4) Containers SQL (PostgreSQL + Adminer)

O `docker-compose.yml` contém:
- **postgres**: banco principal (`localhost:55432`);
- **adminer**: cliente SQL web (`http://localhost:8080`).

### Subir stack SQL
```bash
bash scripts/start_sql_stack.sh
```

### Acesso ao Adminer
- URL: `http://localhost:8080`
- Sistema: `PostgreSQL`
- Servidor: `postgres`
- Usuário: `postgres`
- Senha: `postgres`
- Banco: `quimioanalytics`

---

## 5) Variáveis de ambiente

Valores padrão usados pelo projeto:

```bash
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=localhost
export DB_PORT=55432
export DB_NAME=quimioanalytics
export DB_SCHEMA=quimioanalytics
```

Essas variáveis são lidas por:
- `config/database.py` (conexão SQLAlchemy);
- `scripts/apply_schema.sh`;
- `scripts/run_pipeline.sh`.

---

## 6) Execução passo a passo (manual)

### Passo 1 — Criar ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate
```

### Passo 2 — Instalar dependências
```bash
pip install -r requirements.txt
```

### Passo 3 — Subir containers SQL
```bash
bash scripts/start_sql_stack.sh
```

### Passo 4 — Aplicar schema no PostgreSQL
```bash
bash scripts/apply_schema.sh
```

### Passo 5 — Executar pipeline
```bash
python main.py
```

Resultado esperado:
- criação do experimento;
- carga de amostras/sinais/replicatas;
- cálculo de score e probabilidade;
- ranking Top 5 por sinal;
- enriquecimento molecular e persistência no banco.

---

## 7) Scripts incluídos (automação)

### `scripts/start_sql_stack.sh`
Sobe serviços SQL via Docker Compose e exibe status.

```bash
bash scripts/start_sql_stack.sh
```

### `scripts/apply_schema.sh`
Aplica `database_schema_postgresql.sql` no banco configurado.

```bash
bash scripts/apply_schema.sh
```

### `scripts/run_pipeline.sh`
Bootstrap do ETL: valida Python, cria venv, instala dependências (opcional), aplica schema (opcional) e executa pipeline.

```bash
bash scripts/run_pipeline.sh
```

Parâmetros via ambiente:
- `INSTALL_DEPS=0` desativa reinstalação de dependências;
- `APPLY_SCHEMA=0` desativa aplicação de schema;
- `PYTHON_CMD=python3` força interpretador;
- `IDENT_FILE`/`ABUND_FILE` alteram caminhos de entrada.

### `scripts/run_full_stack.sh`
Executa fluxo completo em sequência: sobe stack SQL, aplica schema e executa ETL.

```bash
bash scripts/run_full_stack.sh
```

---

## 8) Fluxo técnico do pipeline (detalhado)

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

## 9) Troubleshooting

- **`docker: command not found`**
  - instale Docker Desktop/Engine e Docker Compose.
- **`psql: command not found`**
  - instale cliente PostgreSQL no host.
- **Erro de conexão com banco**
  - valide `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`.
  - confirme stack ativa com `docker compose ps`.
- **Timeout em APIs externas (enrichment)**
  - o processo é best-effort; campos podem ficar nulos sem interromper a execução.

---

## 10) Execução recomendada (rápida)

Se o ambiente já possui Docker e `psql`, este comando resolve tudo:

```bash
bash scripts/run_full_stack.sh
```
