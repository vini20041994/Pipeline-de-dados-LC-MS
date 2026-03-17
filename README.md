# Pipeline de dados LC-MS (QuimioAnalytics)

Projeto de ETL para processar planilhas LC-MS, calcular ranking probabilístico Top 5 de candidatos moleculares, enriquecer metadados em bases públicas (PubChem, KEGG, ChEBI, HMDB e MeSH) e persistir em PostgreSQL.

## 1) Organização da documentação

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
- [`scripts/run_pipeline.sh`](scripts/run_pipeline.sh): script automatizado de bootstrap + execução.
- [`docker-compose.yml`](docker-compose.yml): serviços de banco e cliente SQL web.

---

## 2) Pré-requisitos

1. Docker e Docker Compose instalados.
2. Python 3.10+ instalado (caso execute sem Docker para ETL).
3. Arquivos de entrada presentes:
   - `data/identificacao.xlsx`
   - `data/abundancia.xlsx`

---

## 3) Subindo os containers SQL

O projeto possui dois serviços no `docker-compose.yml`:
- **postgres**: banco principal do projeto.
- **adminer**: cliente SQL web para inspeção/consulta.

Execute:

```bash
docker compose up -d
```

Verificação:

```bash
docker compose ps
```

Acesso ao cliente SQL (Adminer):
- URL: `http://localhost:8080`
- Sistema: `PostgreSQL`
- Servidor: `postgres`
- Usuário: `postgres`
- Senha: `postgres`
- Banco: `quimioanalytics`

> Observação: a porta do PostgreSQL está mapeada para `55432` no host.

---

## 4) Configuração de ambiente

Defina variáveis para conexão (opcional, já possuem padrão):

```bash
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=localhost
export DB_PORT=55432
export DB_NAME=quimioanalytics
export DB_SCHEMA=quimioanalytics
```

---

## 5) Execução passo a passo (manual)

### Passo 1 — Criar ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate
```

### Passo 2 — Instalar dependências
```bash
pip install -r requirements.txt
```

### Passo 3 — Aplicar schema no PostgreSQL
```bash
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f database_schema_postgresql.sql
```

### Passo 4 — Executar o pipeline
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

## 6) Execução automatizada (script único)

Para executar tudo de uma vez:

```bash
bash scripts/run_pipeline.sh
```

Esse script:
1. valida o Python disponível;
2. cria `.venv` se necessário;
3. instala dependências;
4. aplica o schema SQL (opcional);
5. executa o `main.py`.

Flags úteis por variável de ambiente:
- `INSTALL_DEPS=0` para não reinstalar dependências;
- `APPLY_SCHEMA=0` para não reaplicar o schema;
- `IDENT_FILE=/caminho/identificacao.xlsx` para arquivo customizado;
- `ABUND_FILE=/caminho/abundancia.xlsx` para arquivo customizado.

Exemplo:

```bash
INSTALL_DEPS=0 APPLY_SCHEMA=0 bash scripts/run_pipeline.sh
```

---

## 7) Estrutura resumida do pipeline

1. **Extract**: leitura de planilhas Excel.
2. **Transform**: padronização e validação de colunas; normalização de abundância.
3. **Score**: cálculo de score final, prior, likelihood e posterior.
4. **Top 5**: seleção dos 5 melhores candidatos por sinal.
5. **Enrich**: consulta de metadados externos.
6. **Load**: persistência transacional no PostgreSQL.

---

## 8) Troubleshooting rápido

- **Erro de conexão no banco**: confirme `DB_HOST/DB_PORT` e se `docker compose ps` mostra `postgres` saudável.
- **`psql` não encontrado**: instale cliente PostgreSQL local ou aplique schema via container.
- **Timeout nas APIs de enriquecimento**: o pipeline segue em best-effort; alguns campos podem ficar nulos.
