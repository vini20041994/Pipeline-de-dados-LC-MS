# Análise do Projeto — QuimioAnalytics

## 1. Clareza do problema e aderência ao cliente

O projeto está bem contextualizado e endereça um problema real da metabolômica:

- grande volume de dados na análise LC-MS;
- identificação manual de compostos;
- múltiplos candidatos para um mesmo sinal;
- necessidade de consulta a diversas bases científicas.

### Impactos do cenário atual

- alto tempo de análise;
- dependência de especialistas;
- baixa escalabilidade.

### Proposta do projeto

- pipeline de dados estruturado;
- integração com bases científicas;
- heurística probabilística para ranqueamento Top 5.

**Conclusão:** aderência forte ao contexto do cliente (IST Ambiental), com boa justificativa acadêmica e aplicada.

---

## 2. Estrutura de Engenharia de Dados

A arquitetura proposta segue um fluxo clássico e adequado para graduação com aplicação real:

1. Ingestão;
2. Transformação;
3. Enriquecimento;
4. Persistência em banco;
5. BI/Dashboard.

Fluxo resumido:

```text
Excel / dados brutos
       ↓
Python ETL
       ↓
APIs científicas
       ↓
PostgreSQL
       ↓
Dashboards BI
```

### Stack tecnológica

- Python;
- Pandas;
- Requests;
- SQLAlchemy;
- PostgreSQL;
- APIs científicas;
- ferramenta de BI.

**Conclusão:** excelente escolha tecnológica, moderna e majoritariamente open source.

---

## 3. Arquitetura de dados

### Camada 1 — Ingestão e transformação

- leitura de planilhas de identificação e abundância;
- transformações tabulares (`melt`, `pivot`) para normalização analítica.

### Camada 2 — Enriquecimento

Integração com bases como:

- PubChem;
- KEGG;
- ChEBI;
- HMDB;
- MeSH.

Essa camada agrega valor científico e aumenta robustez da anotação.

### Camada 3 — Persistência

Uso de banco relacional (PostgreSQL) para:

- rastreabilidade;
- integridade dos dados;
- consultas para replicatas dinâmicas e análises comparativas.

### Camada 4 — Visualização

Dashboard para interpretação por pesquisadores e tomada de decisão.

**Conclusão:** desenho de camadas consistente com boas práticas de Data Engineering.

---

## 4. Modelo matemático (Top 5)

O núcleo analítico propõe ranqueamento probabilístico com base em evidências.

Probabilidade condicional:

\[
P(C_i \mid S_{frag}, S_{base}, S_{iso}) = \frac{P(S_{frag}, S_{base}, S_{iso} \mid C_i) \cdot P(C_i)}{P(S_{frag}, S_{base}, S_{iso})}
\]

Score ponderado:

\[
Score_{final}(C_i) = w_1\,\hat{S}_{frag} + w_2\,\hat{S}_{base} + w_3\,\hat{S}_{iso}
\]

Critérios utilizados:

- `Fragmentation score`;
- `Base score`;
- similaridade isotópica.

Resultado esperado:

- ranking de candidatos por sinal;
- entrega dos 5 mais prováveis (Top 5).

**Conclusão:** proposta tecnicamente sólida e alinhada ao objetivo do cliente.

---

## 5. Organização da equipe

Distribuição de papéis clara e compatível com um time de dados:

| Papel | Responsável |
|---|---|
| Gerência e BI | Samuel |
| Ciência de dados / APIs | Vinícius |
| Banco de dados | Guilherme Anselmo |
| Engenharia de dados ETL | Guilherme Zamboni |

**Conclusão:** estrutura profissional, com responsabilidades bem definidas.

---

## 6. Cronograma

Planejamento temporal coerente para semestre acadêmico:

| Etapa | Período |
|---|---|
| Diagnóstico | Março |
| Banco de dados | Março |
| ETL | Abril |
| Modelo probabilístico | Abril |
| Dashboard | Maio |
| Pitch | Junho |
| Artigo | Julho |

**Conclusão:** cronograma realista, orientado a entregas incrementais.

---

## 7. Pontos fortes

1. **Problema real com cliente real** (IST Ambiental), aumentando relevância prática.
2. **Integração multidisciplinar** entre Engenharia de Dados, Bioinformática, Probabilidade, Banco de Dados e BI.
3. **Uso de APIs científicas** de alto valor para enriquecimento de dados.
4. **Potencial de desdobramento científico** para artigo, TCC e publicação.

---

## 8. Oportunidades de melhoria

1. **Adicionar diagrama de arquitetura** fim a fim.
2. **Incluir modelo ER/schema do banco** para clareza da modelagem.
3. **Detalhar estratégia de integração de APIs**, incluindo:
   - cache;
   - limites de requisição/rate limit;
   - paralelismo e retry.
4. **Definir métricas de sucesso mensuráveis**, por exemplo:
   - tempo médio por amostra antes/depois;
   - taxa de acerto das anotações Top 5;
   - cobertura de enriquecimento por base.

---

## 9. Avaliação geral (acadêmica)

| Critério | Nota |
|---|---|
| Problema | 9.5 |
| Arquitetura | 9.0 |
| Modelagem | 9.0 |
| Tecnologias | 9.0 |
| Clareza | 8.5 |

**Nota estimada:** **9.0 / 10**.

---

## 10. Avaliação profissional (mercado)

O projeto se posiciona como um **mini-produto de bioinformática aplicada**, combinando:

- Data Engineering;
- ranqueamento probabilístico;
- integração com bases científicas.

Tem aderência a contextos de:

- biotech;
- pharma;
- bioinformática;
- pesquisa ambiental.

---

## Próximos passos recomendados

- formalizar os diagramas (arquitetura + ER);
- implementar baseline de métricas de desempenho;
- documentar critérios de calibração dos pesos \(w_1, w_2, w_3\);
- preparar versão executiva para apresentação à banca e ao cliente.
