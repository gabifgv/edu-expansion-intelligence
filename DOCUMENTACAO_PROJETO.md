# FGV Market Intelligence Platform
## Documentação Técnica e de Negócios — Projeto Completo

> **TCC MBA — Fundação Getulio Vargas**
> **Autora:** Gabriella do Nascimento Pinheiro
> **Cliente interno:** Time de Expansão FGV (escolas de MBA e Pós-Graduação)
> **Período de desenvolvimento:** outubro/2025 — maio/2026
> **Status:** 7 blocos validados, pendente consolidação no `index.html` com identidade FGV

---

## SUMÁRIO

1. [Sumário Executivo](#1-sumário-executivo)
2. [Contexto e Motivação de Negócio](#2-contexto-e-motivação-de-negócio)
3. [Arquitetura Técnica](#3-arquitetura-técnica)
4. [Camada de Dados — Fontes e Pipeline](#4-camada-de-dados--fontes-e-pipeline)
5. [Migração BigQuery → DuckDB](#5-migração-bigquery--duckdb)
6. [Os 7 Blocos do Dashboard](#6-os-7-blocos-do-dashboard)
   - [Bloco 1 — Perfil Socioeconômico](#bloco-1--perfil-socioeconômico)
   - [Blocos 2+3 — Mercado de Trabalho + Tecido Empresarial (Fundidos)](#blocos-23--mercado-de-trabalho--tecido-empresarial-fundidos)
   - [Bloco 4 — Empresas-Alvo](#bloco-4--empresas-alvo)
   - [Bloco 5 — Pipeline Universitário](#bloco-5--pipeline-universitário)
   - [Bloco 6 — Score de Atratividade](#bloco-6--score-de-atratividade)
   - [Bloco 7 — Narrativa AI Executiva](#bloco-7--narrativa-ai-executiva)
7. [Workflow de Validação](#7-workflow-de-validação)
8. [Desafios e Decisões Críticas](#8-desafios-e-decisões-críticas)
9. [Estatísticas do Projeto](#9-estatísticas-do-projeto)
10. [Próximos Passos](#10-próximos-passos)
11. [Como Replicar — Guia Passo a Passo](#11-como-replicar--guia-passo-a-passo)
12. [Anexos](#12-anexos)

---

## 1. SUMÁRIO EXECUTIVO

### O que é

A **FGV Market Intelligence Platform** é um dashboard interativo de inteligência de mercado que automatiza a decisão estratégica de **onde a FGV deve abrir um novo campus de MBA ou Pós-Graduação**. Substitui análises manuais de equipe júnior (que levam semanas e dependem de feeling) por uma plataforma data-driven que cruza dados públicos (RAIS, INEP, IBGE, CNPJ) com IA generativa (Claude API) para entregar:

- Análise socioeconômica do município candidato
- Mercado de trabalho formal por setor e cargo
- Lista de empresas-alvo com CNPJ, contato e distância de carro
- Pipeline universitário local (formandos por área)
- Score de atratividade ponderado em 4 dimensões
- Relatório executivo gerado por IA com prioridade de expansão (Alta/Média/Baixa) e cursos recomendados

### Para que serve

Antes da plataforma, a decisão de expansão FGV passava por:
- Pesquisa manual em IBGE, RAIS, INEP (semanas)
- Compra de listas de leads corporativos (custo)
- Reuniões com consultoria (R$ centenas de milhares por estudo)
- "Achismo" de gestores baseado em rede de contatos

A plataforma reduz esse ciclo para **5 minutos por município**, com dados sempre atualizados, custo marginal de R$ 0,30 por análise (chamada Claude API) e resposta executiva acionável.

### Status Atual

| Componente | Status |
|---|---|
| Pipeline dbt (BigQuery → star schema) | ✅ Completo |
| Export para DuckDB local | ✅ Completo (286 MB, ~14 milhões de linhas) |
| Bloco 1 — Perfil Socioeconômico | ✅ Validado |
| Blocos 2+3 — Mercado de Trabalho + Tecido Empresarial | ✅ Validados (fundidos) |
| Bloco 4 — Empresas-Alvo | ✅ Validado (preview HTML) |
| Bloco 5 — Pipeline Universitário | ✅ Validado (preview HTML) |
| Bloco 6 — Score de Atratividade | ✅ Validado (preview HTML) |
| Bloco 7 — Narrativa AI | ✅ Validado (Claude opus-4-7 funcionando) |
| Consolidação `dashboard/index.html` com identidade FGV | 🟡 Pendente |
| Deploy em Cloud Run | 🟡 Pendente |

---

## 2. CONTEXTO E MOTIVAÇÃO DE NEGÓCIO

### Origem do Projeto

Este é um **TCC do MBA executivo da FGV** desenvolvido por Gabriella do Nascimento Pinheiro. O projeto tem um cliente interno real — o time de expansão da FGV — e foi desenhado para entregar valor de negócio imediato, não apenas atender requisitos acadêmicos.

A FGV opera escolas de MBA e Pós-Graduação em diversas praças do Brasil. Periodicamente, surge a pergunta: **"Vale a pena abrir um campus em [cidade X]?"**. A resposta tradicional dependia de:

- Conhecimento de gestores (subjetivo)
- Estudos de mercado terceirizados (caros e demorados)
- Análise manual em planilhas Excel (limitada)

### Hipótese de Negócio

> **Cruzar bases públicas com IA generativa permite uma decisão de expansão fundamentada em dados, em minutos e a custo marginal próximo de zero.**

Os dados existem, são públicos, atualizados anualmente, mas estão **fragmentados em silos** (INEP, RAIS, IBGE, Receita Federal). A inovação é o **cruzamento + síntese executiva via LLM**.

### Público-Alvo

- **Diretor de Expansão FGV** — toma a decisão final
- **Time de Vendas / Captação** — usa para prospecção corporativa
- **Coordenadores de Curso** — identificam temas com demanda

### Posicionamento

Não compete com Tableau / Power BI corporativos — é um **produto vertical, opinionated, focado em uma única decisão**. A interface é simples (HTML estático) e o conteúdo é prescritivo: "**Prioridade Alta**, foco em saúde e finanças, contate Itaú e Bradesco, parceria com UNICAMP e PUC-Campinas."

---

## 3. ARQUITETURA TÉCNICA

### Stack Tecnológico

| Camada | Tecnologia | Justificativa |
|---|---|---|
| **Data Warehouse** | Google BigQuery | Onde dados públicos do `basedosdados.org` já estão hospedados |
| **Transformação** | dbt-bigquery | Versionar lógica SQL, testes, documentação automática |
| **OLAP local** | DuckDB 1.0+ | Dashboard offline, queries em milisegundos, banco em arquivo único de 286 MB |
| **Backend** | FastAPI | Async, type-safe, OpenAPI gratuito, integração trivial com Pydantic |
| **Frontend** | HTML5 + Vanilla JS + Plotly.js | Sem build step, sem framework, leitura direta no browser |
| **LLM** | Claude API (Anthropic) — modelo `claude-opus-4-7` | Capacidade analítica superior, contexto de 200k tokens, raciocínio multi-camada |
| **Geocoding** | BrasilAPI + OSRM | BrasilAPI para CEP→coordenadas (gratuito, sem chave); OSRM para distância de carro (gratuito, batch de 99 pontos) |
| **Deflator IPCA** | API BCB série 433 | Atualizar valores monetários do Atlas 2010 e RAIS 2022 para reais correntes |

### Diagrama de Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA DE FONTES PÚBLICAS (basedosdados.org no BigQuery)        │
│  ─────────────────────────────────────────────────────────────   │
│  • RAIS vínculos       (mercado de trabalho — 13M linhas SP)     │
│  • RAIS estabelecimentos (densidade empresarial)                 │
│  • CNPJ Receita Federal (475k empresas SP médias e grandes)      │
│  • INEP Censo Superior (775k linhas formandos SP)                │
│  • INEP Censo Escolar (formandos ensino médio)                   │
│  • IDEB / INSE escola (qualidade ensino básico)                  │
│  • IBGE Atlas ADH 2010 (IDHM, renda per capita, Gini)            │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                  dbt run --select staging
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA STAGING (raw_staging) — views                            │
│  Cast, trim, CASE decode (subsetor IBGE, modalidade ensino)      │
│  9 modelos: stg_rais_vinculos, stg_rais_estabs, stg_cnpj,        │
│             stg_inep_grad, stg_inep_form_em, stg_ideb,           │
│             stg_inse, stg_munic_socio_educ                       │
└──────────────────────────────┬───────────────────────────────────┘
                               │
              dbt run --select facts dimensions
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA FACTS + DIMENSIONS (raw_facts, raw_dimensions) — tables  │
│  STAR SCHEMA:                                                    │
│  ┌──────────────────────┐                                        │
│  │ dim_municipio (645)  │ ← chave central                        │
│  └──────────┬───────────┘                                        │
│             │                                                     │
│   ┌─────────┴────────┬────────┬─────────┬────────────┐          │
│   ▼                  ▼        ▼         ▼            ▼          │
│  fct_empregos    fct_estabs  fct_emp  fct_form_em  fct_merc_sup │
│  (13M)           (603k)     (475k)   (?)          (775k)        │
│                                                                  │
│  Grão: id_municipio + ano + setor (quando aplicável)             │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                python data/exportar_sp.py
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA OLAP LOCAL — data/sp_mvp.duckdb (311 MB)                 │
│  Filtrado para sigla_uf='SP': 645 municípios                     │
│  • dim_municipio: 645 linhas                                     │
│  • fct_empregos: 13.216.062 linhas (anos 2020–2024)              │
│  • fct_estabelecimentos: 603.308 linhas (2020–2024)              │
│  • fct_empresas: 475.574 linhas (snapshot mais recente)          │
│  • fct_mercado_superior: 775.028 linhas (anos 2020–2024)         │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                python data/teste_b*.py
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA DE VALIDAÇÃO (terminal + previews HTML)                  │
│  Cada bloco testado isoladamente antes de integrar               │
│  data/teste_b1.py, b23.py, b4.py, b5.py, b6.py, b7.py            │
│  data/preview_b4.html, b5.html, b6.html, b7.html                 │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                       (integração futura)
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA DE APLICAÇÃO — FastAPI + HTML                            │
│  • dashboard/app.py: 155 linhas, 7 endpoints                     │
│  • dashboard/queries.py: 519 linhas, 1 query por bloco           │
│  • dashboard/index.html: 755 linhas, identidade FGV (azul navy)  │
│                                                                  │
│  Endpoints:                                                      │
│  GET  /                       → serve index.html                 │
│  GET  /api/ufs                → lista 27 UFs                     │
│  GET  /api/municipios/{uf}    → municípios da UF                 │
│  POST /api/analise            → blocos 1–6 (síncrono, ~2s)       │
│  POST /api/analise-llm        → bloco 7 (Claude API, ~15s)       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. CAMADA DE DADOS — FONTES E PIPELINE

### 4.1 Fontes Públicas Utilizadas

Todas as fontes vêm do **`basedosdados.org`** — projeto que disponibiliza dados públicos brasileiros já tratados no BigQuery.

| Fonte | Origem | Período | Granularidade | Uso |
|---|---|---|---|---|
| **RAIS Vínculos** | Ministério do Trabalho via `br_me_rais.microdados_vinculos` | 2020–2024 | município × subsetor × CNAE × cargo × ano | Mercado de trabalho, salários, elegibilidade |
| **RAIS Estabelecimentos** | `br_me_rais.microdados_estabelecimentos` | 2020–2024 | município × CNAE × ano | Densidade empresarial |
| **CNPJ Receita Federal** | `br_me_cnpj.empresas` + `.estabelecimentos` | Snapshot mais recente | CNPJ | Empresas médias e grandes (porte 5) |
| **INEP Censo Superior** | `br_inep_censo_superior.curso` | 2020–2024 | curso × IES × município × ano | Formandos, IES locais, áreas em alta |
| **INEP Censo Escolar (turma)** | `br_inep_censo_escolar.turma` | 2020+ | escola × município × ano | Formandos do EM (não usado nos 7 blocos atuais) |
| **IDEB escola** | `br_inep_ideb.escola` | 2020–2023 | escola × ano | Qualidade ensino básico (não usado nos 7 blocos) |
| **INSE escola** | `br_inep_indicador_nivel_socioeconomico.escola` | 2023 | escola | Nível socioeconômico aluno (não usado nos 7 blocos) |
| **IBGE Atlas ADH** | `mundo_onu_adh.municipio` | 2010 | município | IDHM, renda per capita, Gini, taxa superior 25+ |

### 4.2 Camada Staging (dbt views)

**Princípio:** views simples, uma por fonte, fazem cast/trim/CASE decode. **Sem joins**. O objetivo é normalizar tipos e decodificar valores enumerados (ex: `subsetor_ibge=23` → `'Ensino'`).

Exemplo (`stg_rais_vinculos_municipio.sql`):

```sql
case cast(subsetor_ibge as integer)
    when 1  then 'Extrativismo Mineral'
    when 13 then 'Indústria de Produtos Alimentícios, Bebidas e Álcool'
    when 18 then 'Instituições de Crédito, Seguros e Capitalização'
    when 19 then 'Comércio e Administração de Imóveis e Serviços Técnicos'
    when 23 then 'Ensino'
    when 24 then 'Administração Pública Direta e Autárquica'
    -- ... 25 subsetores no total
end as descricao_subsetor
```

**Modelos staging (9):**
- `stg_rais_vinculos_municipio.sql` (65 linhas)
- `stg_rais_estabelecimentos_municipio.sql` (61)
- `stg_cnpj_empresas.sql` (49)
- `stg_inep_graduacao.sql` (49)
- `stg_inep_graduacao_fgv.sql` (68 — criado mas removido do uso final)
- `stg_inep_formandos_ensinomedio.sql` (32)
- `stg_ideb_escola.sql` (44)
- `stg_inse_escola.sql` (45)
- `stg_munic_socio_educ.sql` (56)

### 4.3 Camada Star Schema (dimensions + facts)

**Decisão arquitetural:** seguimos rigorosamente o padrão de **modelagem estrela**:
- 1 dimensão central: `dim_municipio` (51 linhas SQL)
- 8 fatos agregados, cada um com `id_municipio` + `ano` como chaves

**Dimensão (`dim_municipio`)** — 645 linhas para SP:
- Chaves: `id_municipio` (IBGE 7 dígitos), `nome_municipio`, `sigla_uf`
- Desenvolvimento humano: `idhm`, `idhm_educacao`, `idhm_renda`, `faixa_idhm`
- Renda e desigualdade: `renda_per_capita`, `indice_gini`
- População: `populacao_total`, `populacao_urbana`, `populacao_15_17`, `populacao_16_18`, `populacao_18_24`
- Educação: `taxa_freq_liquida_medio`, `taxa_freq_bruta_superior`, `taxa_medio_18_24`, `taxa_superior_25_mais`
- Vulnerabilidade: `prop_pobreza`

**Fatos (8 modelos):**

| Modelo | Linhas SQL | Grão | Métricas principais |
|---|---|---|---|
| `fct_empregos` | 30 | município × ano × subsetor × CNAE × cargo | total_vinculos, salario_medio_reais, salario_medio_sm |
| `fct_estabelecimentos` | 26 | município × ano × subsetor × CNAE | total_estabelecimentos, total_vinculos_ativos |
| `fct_empresas` | 34 | CNPJ | nome_empresa, cnae_classe, capital_social, porte, cep, ddd, telefone, email |
| `fct_mercado_superior` | 38 | curso × IES × município × ano × modalidade | total_vagas, total_inscritos, total_ingressantes, total_matriculas, total_concluintes |
| `fct_formandos_em` | 23 | escola × ano | total_formandos (não usado no MVP) |
| `fct_ideb_escola` | 28 | escola × ano | ideb, taxa_aprovacao, nota_saeb (não usado no MVP) |
| `fct_inse_escola` | 31 | escola | inse, classificacao (não usado no MVP) |
| `fct_mercado_fgv` | 52 | curso × IES × município × ano | versão filtrada para FGV (não usado no MVP) |

**Decisão importante:** o dashboard **NÃO** lê de marts pré-calculados. Lê direto do star schema, mantendo a série histórica e calculando KPIs em runtime. Marts são reservados para projetos de ML futuros.

### 4.4 Pipeline dbt → BigQuery → DuckDB

```bash
# Passo 1: rodar staging (views, lazy)
dbt run --select staging

# Passo 2: rodar facts e dimensions (tables, materialized)
dbt run --select facts dimensions

# Passo 3: testar
dbt test

# Passo 4: exportar para DuckDB local (1x, demora ~30 min)
python data/exportar_sp.py
```

O script `exportar_sp.py` (102 linhas) faz a query no BigQuery filtrando `sigla_uf='SP'`, exporta ano a ano para tabelas grandes (`fct_empregos` tem 13M linhas) e salva em `data/sp_mvp.duckdb`.

---

## 5. MIGRAÇÃO BIGQUERY → DUCKDB

### Por que migramos

A primeira versão do dashboard (`dashboard/queries.py` — 519 linhas) lia direto do BigQuery a cada chamada `POST /api/analise`. Problemas:

1. **Latência:** cada query cobrava ~1.5s de network round-trip. 7 blocos = ~10s de espera.
2. **Custo:** queries em produção em uma tabela de 13M linhas custam centavos por chamada — multiplicado por 100 análises/dia, vira centenas de reais/mês.
3. **Dependência de auth:** OAuth do Google expira a cada 30 dias, frustrante em dev.
4. **Ambiente offline:** TCC apresentado em sala — Wi-Fi pode falhar.

### Solução: DuckDB Local

DuckDB é um SGBD analítico em arquivo único que executa queries OLAP em milissegundos. Filtramos os ~14M de linhas para SP (universo do MVP) e salvamos em `data/sp_mvp.duckdb` (311 MB).

| Métrica | BigQuery | DuckDB local |
|---|---|---|
| Latência por query | 1–3 s | 50–200 ms |
| Custo | ~R$ 0,02 / chamada | R$ 0 |
| Ambiente | Online apenas | Offline |
| Setup | OAuth | Arquivo |

### Trade-offs

- **Dados estáticos:** DuckDB local é um snapshot. Para refresh, rodar `exportar_sp.py` novamente (rodada anual no MVP).
- **Apenas SP:** dashboard atual filtra SP. Para nacional, gerar arquivos por UF e selecionar dinamicamente.
- **Tamanho:** 311 MB é grande para distribuir. No deploy, montaria via volume Cloud Run.

### Reescrita de queries.py

A versão atual de `dashboard/queries.py` ainda usa BigQuery. **Pendência arquitetural:** reescrever para DuckDB no momento da consolidação do `index.html`.

---

## 6. OS 7 BLOCOS DO DASHBOARD

> **Convenção do projeto:** cada bloco tem 2 artefatos:
> - `data/teste_bX.py` — script terminal validando lógica e mostrando dados brutos
> - `data/preview_bX.py` (gera `preview_bX.html`) — protótipo visual standalone

### BLOCO 1 — PERFIL SOCIOECONÔMICO

#### O que mostra
Tabela comparando o município escolhido vs. **média ponderada da UF** (não simples média) em 8 métricas:

| Indicador | Campinas | Média SP (ponderada) | Delta | Status |
|---|---|---|---|---|
| IDHM geral | 0.805 | 0.752 | +7.0% | ACIMA ✅ |
| Renda per capita | R$ 3.374 | R$ 2.146 | +57.2% | ACIMA ✅ |
| Renda média RAIS 2022 | R$ 4.890 | R$ 3.421 | +43% | ACIMA ✅ |
| Índice de Gini | 0.560 | 0.542 | +3.3% | abaixo (Gini maior = pior) |
| População total | 1.080.113 | — | — | neutro |
| Pop. 25+ c/ superior | 21.3% | 14.8% | +43.9% | ACIMA ✅ |
| Prop. em pobreza | 3.2% | 6.5% | -50.7% | ACIMA ✅ (menor é melhor) |
| **Elegíveis / vínculos** | **39.9%** | **38.5%** | **+1.4 pp** | **ACIMA ✅** |

#### Por que importa
- Define se a cidade tem **público maduro** o suficiente para um produto premium
- IDHM + renda alta = mercado preparado, baixo risco de inadimplência
- Taxa superior 25+ alta = base instalada de elegíveis para pós-graduação
- A última linha (% elegíveis) é o **insight prático**: quanto da força de trabalho consegue pagar a mensalidade?

#### Decisões técnicas

**1. Deflator IPCA dinâmico:**
- Atlas ADH usa valores de **agosto/2010** → deflacionar para 2026 (fator ~2.42x)
- RAIS usa salários de **dezembro/2022** → deflacionar para 2026 (fator ~1.17x)
- Buscado em runtime via API BCB série 433, com fallback hardcoded se a API falhar

```python
url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={data_ini}"
fator = 1.0
for d in dados:
    fator *= (1 + float(d["valor"]) / 100)
```

**2. Média ponderada por população:**
- Média simples distorce: cidades pequenas com IDHM alto inflam a média estadual
- Solução: `SUM(idhm * populacao_total) / SUM(populacao_total)`
- Resultado: a "média SP" reflete onde o paulista típico vive

**3. Renda mínima dinâmica:**
- Input: mensalidade (ex: R$ 1.200) e % da renda dedicado (ex: 9%)
- Cálculo: `renda_min = mensalidade / (% / 100)` = R$ 13.333 ou ajustado para 30% = R$ 4.000
- Quem ganha menos que isso é considerado **inelegível** ao produto

#### Validação
Script: `data/teste_b1.py` (124 linhas)
Output em terminal mostra tabela completa para Campinas vs SP — usado para alinhamento com a equipe FGV antes de codificar HTML.

---

### BLOCOS 2+3 — MERCADO DE TRABALHO + TECIDO EMPRESARIAL (FUNDIDOS)

#### Por que foram fundidos
Originalmente eram dois blocos separados:
- **Bloco 2:** mercado de trabalho RAIS por subsetor
- **Bloco 3:** densidade empresarial (estabelecimentos)

Na validação, percebemos que:
- A pergunta do usuário não é "quantos estabelecimentos existem" nem "quantos vínculos formais existem", é **"qual setor combina muitos elegíveis + muitas empresas?"** — i.e., onde fazer prospecção corporativa?
- Fundir as duas em uma única tabela permite calcular **`func/empresa`** (vínculos ÷ estabelecimentos), métrica chave de tamanho médio de empresa no setor.

#### O que mostra

**Tabela 1 — Por Setor** (26 setores IBGE):

| Setor | Estabs | Func/emp | Vínculos | Sal.médio | Eleg. | %eleg | Sal.eleg |
|---|---|---|---|---|---|---|---|
| Comércio e Administração de Imóveis... | 12.453 | 8 | 100.294 | R$ 4.821 | 45.054 | 44.9% | R$ 9.514 |
| Ensino | 1.823 | 21 | 38.226 | R$ 5.692 | 24.734 | 64.7% | R$ 8.452 |
| Administração Pública | 412 | 58 | 23.923 | R$ 8.294 | 21.185 | 88.6% | R$ 10.231 |
| Transportes e Comunicações | 2.156 | 15 | 32.570 | R$ 4.213 | 12.430 | 38.2% | R$ 7.892 |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Tabela 2 — Por Cargo** (top 20 de 536 cargos com elegíveis):
- Multi-select de setor acima da tabela (filtragem client-side)
- Permite mergulhar: quais cargos específicos no setor de Ensino têm renda alta?

#### Por que importa
- O setor com maior **% elegíveis** é onde a abordagem por turma fechada faz mais sentido
- Cargos específicos guiam o **tema do curso a ser ofertado** (ex: 12k Analistas de Sistemas → MBA Transformação Digital)
- "Func/empresa" indica se o setor é dominado por **PMEs** (1-10 func/emp) ou **grandes empresas** (50+ func/emp), influenciando estratégia B2B

#### Decisões técnicas

**1. Filtro `elegíveis < 5`:**
- Quando uma célula tem 1-2 elegíveis, o "salário médio dos elegíveis" pode ser uma anomalia
- Solução: mostrar "-" em vez de número quando elegíveis < 5
- Evita que outliers de 1-2 funcionários pareçam tendências

**2. Exclusão de "Não Classificado":**
- Setor `Não Classificado` aparece quando o subsetor IBGE não foi mapeado
- Não tem match em `fct_estabelecimentos` (não há estabs sem CNAE)
- Excluído com `WHERE es.estabs IS NOT NULL`

**3. Multi-select de setor com filtragem client-side:**
- 26 setores fixos
- Frontend faz `filter()` em JavaScript no JSON pré-carregado
- Sem chamadas adicionais ao backend

#### Validação
Script: `data/teste_b23.py` (119 linhas)
Output em terminal com 2 tabelas formatadas, colunas alinhadas.

---

### BLOCO 4 — EMPRESAS-ALVO

#### O que mostra
Lista de empresas **médias e grandes (porte 5)** ativas no município, com dados de contato e **distância de carro** ao endereço da gestora local FGV (CEP digitado pelo usuário).

| Empresa | Setor | CEP | Distância | Telefone | Email |
|---|---|---|---|---|---|
| ITAU UNIBANCO HOLDING S.A. | Inst. de Crédito, Seguros... | 13050-345 | 4.2 km | (19) 3236-0000 | contato@itau.com |
| BRADESCO PA - POLIS DE TECNOLOGIA | Inst. de Crédito... | 13083-852 | 6.8 km | (19) 3251-9000 | contato@bradesco |

#### Por que importa
- Lista de **leads B2B prontos** com CNPJ, contato e geolocalização
- Distância em km informa logística de eventos in-company
- Filtro por capital social mínimo separa **SPEs/holdings vazias** de **empresas operacionais reais**

#### Decisões técnicas

**1. Filtro `porte = '5'` + `capital_social >= R$ 500K` (ajustável):**
- A Receita Federal classifica porte como `5 = Demais` (médias e grandes), `1-4` (microempresa, pequena, EIRELI)
- Mas porte 5 inclui SPEs e holdings com capital de R$ 1.000 — sem operação real
- Solução: dropdown de faixas (R$ 100K, 500K, 1M, 2M, 5M, 10M, "Qualquer valor")
- Padrão sugerido: R$ 500K — separa empresas operacionais de holdings vazias

**2. CNAE classe vs. setor IBGE:**
- `fct_empresas.cnae_classe` (4 dígitos) é diferente de `fct_empregos.descricao_subsetor` (texto IBGE)
- Mapeamento via lookup: para cada `cnae_classe`, qual o `descricao_subsetor` mais frequente (por SUM(vínculos))?
- Implementado com `DISTINCT ON (cnae_classe) ... ORDER BY cnae_classe, v DESC`
- 10 classes têm múltiplos setores; resolve-se pelo mais comum

**3. Distância de carro via OSRM (não linha reta):**
- Inicialmente usamos haversine (linha reta) — incorreto
  - Reclamação: "Vitorio Bim Participações está a 4.2km no Google, não 0.8km em linha reta"
- Solução: OSRM (Open Source Routing Machine) `router.project-osrm.org`
- API gratuita, sem chave, batch de 99 waypoints por request
- Fallback: se OSRM falhar, usa haversine

```python
url = (f"http://router.project-osrm.org/table/v1/driving/{waypts}"
       f"?sources=0&annotations=distance")
# distances vêm em metros, dividir por 1000
```

**4. Paginação client-side com 15 linhas/página:**
- 30 empresas por padrão é muito; 15 é o sweet spot para vendedores
- Frontend faz slice no array; sem chamada adicional ao backend
- Ordenação por coluna (qualquer): clique no header inverte direção

#### Validação
- `data/teste_b4.py` (109 linhas) — terminal validation
- `data/preview_b4.py` + `data/preview_b4.html` (352 linhas Python, ~400 linhas HTML gerado)

---

### BLOCO 5 — PIPELINE UNIVERSITÁRIO

#### O que mostra
1. **KPIs:** concluintes 2024, IES locais, variação 2023→2024 e 2020→2024
2. **Série temporal:** concluintes ano a ano (presencial + EaD)
3. **Tabela:** área × curso × IES × concluintes
4. **Cursos em alta:** crescimento 2020→2024 com volume mínimo
5. **Filtros:** área, curso, IES (multi-select)

#### Por que importa
- Pipeline acadêmico = **futuros candidatos a pós/MBA**
- Quem se forma em Engenharia → MBA Gestão de Projetos
- Quem se forma em Administração → MBA Finanças, Marketing, Gestão Empresarial
- Cursos em alta = áreas com **demanda crescente** local
- IES locais = potenciais **parceiros de captação** (recém-formados)

#### Decisões técnicas

**1. Tratamento de reclassificação INEP 2024:**

A INEP reclassificou seu CINE Brasil em 2024:
- Cursos antigos: "Gestão e desenvolvimento de sistemas de informação", "Ciência da computação", "Produção de software", "Desenvolvimento de sistemas que integram software e hardware"
- Curso novo (2024): **"Análise e desenvolvimento de algoritmos e aplicações"**
- Os 4 antigos somavam ~2.500 concluintes/ano; o novo aparece "do nada" com 7,6% de share

Sem tratamento, mostraríamos: "Análise e desenvolvimento de algoritmos = curso novo, +∞% crescimento" — falso!

Solução implementada em **JavaScript no preview**:

```javascript
function buildAreaBaseline(rows, yearNew, yearOld) {
  // Para cada (area, curso): se curso existia em yearOld mas sumiu em yearNew, marca
  const by = {};
  rows.filter(r => r.y === yearNew || r.y === yearOld).forEach(r => {
    const k = r.a + '|||' + r.c;
    if (!by[k]) by[k] = {area: r.a, cNew: 0, cOld: 0};
    if (r.y === yearNew) by[k].cNew += r.n; else by[k].cOld += r.n;
  });
  // Agrega baseline por área (soma dos cursos que sumiram)
  const base = {};
  Object.values(by).forEach(r => {
    if (r.cNew === 0 && r.cOld > 0) base[r.area] = (base[r.area] || 0) + r.cOld;
  });
  return base;
}
```

A função é **genérica** — não hardcoded para TIC. Funciona para qualquer reclassificação futura ou outra cidade.

**2. Filtros client-side com Plotly.react():**
- Todos os 15.537 registros de Campinas carregados em JSON
- Filtros (area, curso, IES) feitos em JavaScript no array
- `Plotly.react()` recalcula gráficos sem reload
- Tabelas re-renderizam via DOM updates

**3. Bigquery `id_curso` join:**
- Bug histórico: `co_curso` do Excel FGV ≠ `id_ies` INEP
- Fix em commit anterior: `c608a6d fix: join fct_mercado_fgv por id_curso (co_ies do Excel != id_ies INEP)`

#### Validação
- `data/teste_b5.py` (194 linhas) — output em terminal SP inteiro
- `data/preview_b5.py` (471 linhas) → `preview_b5.html` (~600 KB de HTML autocontido com Plotly inline)

---

### BLOCO 6 — SCORE DE ATRATIVIDADE

#### O que mostra
Score 0–100 do município, calculado a partir de **4 dimensões com pesos ajustáveis pelo usuário** via sliders:

- **D1 Capacidade de Pagamento** (default 35%) — quem pode pagar
- **D2 Tamanho de Mercado** (default 30%) — quantos podem pagar
- **D3 Pipeline Acadêmico** (default 20%) — quem está se formando
- **D4 Dinamismo Econômico** (default 15%) — está crescendo?

Ranking dos **645 municípios SP** com:
- KPI "Maior score" + "Rank do município selecionado"
- Gráfico top 20 (Campinas destacada em verde)
- Radar chart das 4 dimensões para a cidade clicada
- Tabela paginada com busca, ordenação por qualquer coluna

#### Por que importa
- Permite **comparar** rapidamente cidades dentro do estado
- Sliders permitem testar cenários: "e se eu valorizar mais Pipeline Acadêmico?"
- Score é **transparente** — usuário vê os 4 componentes, não só o número final
- Coluna "motivo" no terminal explica posição: "↑Pipeline (59) ↓Tam.Mercado (12)"

#### Decisões técnicas

**1. Min-max normalization dentro do estado:**
- Cada sub-indicador é normalizado para [0, 1] usando `(x - min) / (max - min)`
- Normalização é **dentro do estado** — não cross-state
- Justificativa: comparar Campinas com São Paulo capital faz sentido; com Rio de Janeiro não.

**2. Sub-indicadores por dimensão:**

| Dim | Sub-indicador A | Sub-indicador B |
|---|---|---|
| **D1** | Salário médio (ponderado por vínculos) | % vínculos com salário ≥ 3 SM |
| **D2** | Total vínculos formais | Empresas porte grande capital >R$1M / 1.000 vínculos |
| **D3** | Taxa pop 25+ com superior | Concluintes alvo (Negócios+TIC+Eng) / 1.000 hab |
| **D4** | IDHM | Crescimento vínculos 2020→2024 |

Score da dimensão = média dos dois sub-indicadores normalizados.
Score final = `0.35*D1 + 0.30*D2 + 0.20*D3 + 0.15*D4` (× 100 para escala 0–100).

**3. Anomalias capturadas:**

A normalização min-max revela anomalias de **um polo industrial em cidade pequena**:
- Gavião Peixoto: rank #2 (D1=100 — maior salário médio do estado, por causa da Embraer)
- Paulínia: rank #3 (D1=70 — refinaria Petrobras)
- Lavínia: rank #15 (D1=76 — uma indústria isolada)

Mas D2 desses municípios é 4-8/100 (mercado minúsculo). O usuário **vê isso explicitamente** e entende que não há volume real, mesmo o salário médio sendo alto. Insight acionável.

**4. Pesos ajustáveis client-side:**
- Sliders 0-100 em cada dimensão
- Total normalizado dinamicamente (se total ≠ 100, divide pelo total)
- Ranking recalcula em tempo real (`Plotly.react()` + re-render da tabela)

**5. Cobertura completa SP:**
- 645/645 municípios em `dim_municipio`
- 645/645 em `fct_empresas` e `fct_empregos`
- 477/645 em `fct_mercado_superior` 2024 (168 municípios pequenos sem campus = 0 concluintes — correto)

#### Por que escolhemos estas dimensões

A discussão evolutiva foi:

1. **V1 (descartada):** 4 dimensões fixas com pesos hardcoded
   - Problema: "cada usuário tem prioridade diferente" (CFO valoriza pagamento, CMO valoriza mercado)
2. **V2 (atual):** mesmas 4 dimensões + sliders
   - Cada usuário define seus pesos, ranking dinâmico
3. **Veredito:** se cursos de Negócios estão em queda (Bloco 5), D3 captura isso via "concluintes alvo" — não precisamos adicionar dimensão "tendência setorial" separada

#### Validação
- `data/teste_b6.py` (202 linhas) — terminal com top 30, bottom 10, motivo de cada posição
- `data/preview_b6.py` (473 linhas) → `preview_b6.html`

---

### BLOCO 7 — NARRATIVA AI EXECUTIVA

#### O que mostra
Botão "**⚡ Gerar análise**" que aciona o Claude API. O LLM recebe os KPIs dos blocos 1–6 + portfólio de cursos FGV + cursos de concorrentes, e devolve um relatório executivo de 6 seções:

1. **Perfil da Cidade** — quem mora aqui, o que os dados socioeconômicos revelam
2. **Mercado de Trabalho** — setores e cargos com mais elegíveis, ticket viável
3. **Cursos Recomendados** — em **3 camadas:**
   - **Camada 1:** Setor → Pós (qual MBA combina com cada setor dominante)
   - **Camada 2:** Graduação → Pós (quem se forma em X quer fazer pós em Y)
   - **Camada 3:** Gaps de portfólio (cursos que concorrentes têm e FGV não tem, com fit local)
4. **Prospecção Corporativa** — empresas reais do Bloco 4 com modelo de abordagem
5. **Parcerias Acadêmicas** — top 3 IES locais para parceria
6. **Veredito Estratégico** — Prioridade **Alta/Média/Baixa** com justificativa

#### Por que importa
Esta é a **maior alavanca de valor** do projeto. Antes:
- Diretor de Expansão recebe 6 telas de KPIs e tem que sintetizar mentalmente
- Síntese boa exige experiência setorial; júniors fazem síntese genérica

Com o Bloco 7:
- Síntese gerada em ~15 segundos
- Cita números reais (não inventa)
- Recomenda cursos do **portfólio FGV** pelos nomes exatos
- Aponta **lacunas competitivas** (cursos que ESPM/Mackenzie/PUC têm e FGV não)
- Custa ~R$ 0,30 por análise (claude-opus-4-7)

#### Decisões técnicas e de prompt

**1. Modelo: `claude-opus-4-7`**
- Capacidade analítica superior para raciocínio multi-camada
- Contexto 200k tokens (suficiente para os 600 cursos de concorrentes + 123 cursos FGV + dados dos blocos 1-6)
- Custo: ~$0.015 input / $0.075 output por 1k tokens

**2. Tamanho do contexto enviado:**
- Total ~12.000 tokens de input (entre 30k caracteres)
- ~4.500 tokens de output (relatório completo de 6 seções)
- Custo total por análise: ~R$ 0,30

**3. SYSTEM prompt (define persona):**
```
Você é especialista sênior em pesquisa e análise de mercado para portfólio
de MBA e pós-graduação da Fundação Getulio Vargas (FGV).
Seu público é o Diretor de Expansão, que lê para decidir — não para se
informar genericamente.
Escreva com autoridade analítica: cite números dos dados fornecidos,
não use introduções genéricas, cada seção abre direto no insight.
Tom executivo, parágrafos densos de 4 a 6 linhas.
Quando citar empresas e IES, use os nomes exatos fornecidos nos dados.
Nunca invente dados — use apenas o que está no contexto fornecido.
```

**4. USER prompt (dinâmico, ~13k tokens):**
- Dados do município (Bloco 1): IDHM, renda, escolaridade
- Mercado de trabalho (Bloco 2+3): vínculos, elegíveis, top setores e cargos
- Empresas-alvo (Bloco 4): top 5 com nomes reais
- Pipeline universitário (Bloco 5): concluintes, IES, cursos em alta
- Score (Bloco 6): D1-D4 + rank no estado
- **Portfólio FGV ativo:** 123 cursos (lista completa)
- **Cursos concorrentes:** 600 cursos únicos (escola + nome) de 18 escolas
- **Instruções específicas para cada uma das 6 seções**

**5. Decisões de regra (definidas pela cliente Gabriella):**

> Estas regras estão registradas em memória em
> `feedback_bloco7_prompt.md` e devem ser preservadas em iterações futuras:

- **NÃO usar `fgv-depara.xlsx`** — esse arquivo mapeia cursos de graduação INEP a categorias FGV; não é relevante para MBA/Pós
- **Concorrentes:** apenas escola + nome do curso, **sem distinção geográfica** (não filtrar por cidade/campus)
- **Propósito da lista de concorrentes:** identificar cursos que concorrentes têm e FGV não tem, com fit local — sugerir como **lacuna de portfólio**
- **Match obrigatório setor + graduação → pós:**
  - Quem trabalha em **TI** + graduado em **Ciência da Computação** → MBA Transformação Digital, IA & Analytics
  - Quem trabalha em **Finanças** + graduado em **Administração** → MBA Finanças Corporativas
  - Esta lógica deve estar explícita na seção 3 (Cursos Recomendados)

**6. Output structure (forçada no prompt):**
```
**1. Perfil da Cidade**
**2. Mercado de Trabalho**
**3. Cursos Recomendados**
   CAMADA 1 — Setor → Pós
   CAMADA 2 — Graduação → Pós
   CAMADA 3 — Gaps de portfólio
**4. Prospecção Corporativa**
**5. Parcerias Acadêmicas**
**6. Veredito Estratégico**
```

**7. Pré-renderização para previews:**
- `teste_b7.py` salva narrativa em `data/narrativa_campinas.txt`
- `preview_b7.py` lê o arquivo e injeta no HTML — preview funciona standalone
- No dashboard final, FastAPI gera narrativa em runtime

#### Exemplo real — Veredito do Claude para Campinas

> **Prioridade: ALTA.** Campinas combina (i) base de 180 mil profissionais elegíveis com salário médio de R$ 9.512 — o ticket de R$ 1.200/mês representa apenas 12,6% da renda, **folga material para captação e até para upsell**; (ii) pipeline acadêmico de 16.867 concluintes/ano com forte crescimento em saúde (vetor onde FGV tem portfólio robusto e onde o gap competitivo de "Gestão de Clínicas" precisa ser fechado); (iii) presença ancorada de Itaú e Bradesco viabilizando estratégia B2B de turmas fechadas no setor financeiro, segmento de margem alta. O score 42,5/100 (rank #4 em SP) é deprimido pelo D2 Tamanho de Mercado (12/100) — limitação real de volume absoluto frente à capital — mas D1 Capacidade de Pagamento (57) e D3 Pipeline Acadêmico (59) sustentam tese de **praça premium e não de volume**. Recomendação: entrada com portfólio enxuto e curado (Saúde + Finanças + Gestão Pública + TI/Transformação Digital), modelo híbrido com âncora presencial em Barão Geraldo, e estratégia B2B prioritária com Itaú/Bradesco no primeiro ciclo.

Esse parágrafo, escrito por um analista sênior humano, custaria R$ 5.000–10.000 de consultoria. Aqui custou R$ 0,30 e ~15 segundos.

#### Validação
- `data/teste_b7.py` (217 linhas) — chama API, salva narrativa
- `data/build_prompt_b7.py` (137 linhas) — monta SYSTEM + USER template, salva em `data/prompt_b7.json`
- `data/preview_b7.py` (303 linhas) → `preview_b7.html`
- `data/narrativa_campinas.txt` — output completo da última execução

---

## 7. WORKFLOW DE VALIDAÇÃO

A regra de ouro do projeto, definida pela cliente Gabriella desde o início:

> **"Não construir nada sem antes mostrar o plano e os dados."**

Esta regra está registrada em memória (`feedback_nao_construir_sem_revisar.md`).

### Ciclo padrão por bloco

```
1. DESIGN
   └─> Discussão no chat: "o que esse bloco precisa mostrar e por quê"
       ├─> Métricas mais importantes
       ├─> Filtros necessários
       └─> Possíveis anomalias a tratar

2. VALIDAÇÃO TÉCNICA
   └─> teste_bX.py → output em terminal
       ├─> Tabelas formatadas com números reais
       ├─> Iteração rápida (segundos por execução)
       └─> Aprovação da Gabriella antes de codificar UI

3. PROTOTIPAGEM VISUAL
   └─> preview_bX.py → preview_bX.html
       ├─> HTML standalone, sem dependências server-side
       ├─> Embute dados reais no JSON pré-carregado
       ├─> Plotly + DOM puro (sem framework)
       └─> Aprovação visual antes de integrar

4. APROVAÇÃO FORMAL
   └─> "aprovado, vamos para o próximo bloco"
       └─> Bloco anterior é tratado como locked

5. INTEGRAÇÃO (próxima fase)
   └─> Consolidação no dashboard/index.html
       └─> FastAPI passa a ler de DuckDB local
```

### Por que esse workflow funciona

- **Zero retrabalho de UI:** lógica é validada antes de codificar visual
- **Cliente vê dados reais cedo:** fica óbvio se uma métrica está errada
- **Cada bloco é independente:** se um pivota, outros não quebram
- **Documentação implícita:** os scripts de teste viram referência
- **Velocidade:** validar no terminal é 10x mais rápido que validar em HTML

---

## 8. DESAFIOS E DECISÕES CRÍTICAS

Documentação dos principais obstáculos enfrentados e como foram superados — útil para quem replicar o projeto.

### 8.1 CNAE no RAIS — 99% nulo
**Problema:** O campo `cnae_2` em `fct_empregos` (originário de `rais_vinculos`) está 99% nulo.
**Impacto:** queries que tentam fazer join via CNAE falham massivamente.
**Solução:**
- Usar `descricao_subsetor` (campo IBGE, sempre preenchido) como dimensão setorial
- Para empresas (`fct_empresas`), criar coluna pré-computada `cnae_classe` (4 dígitos) via `ALTER TABLE`
- Mapeamento `cnae_classe → setor IBGE` via `DISTINCT ON` pegando o mais frequente

### 8.2 Reclassificação INEP 2024
**Problema:** INEP consolidou 4 cursos de TIC em 1 novo em 2024. Sem tratamento, o curso novo aparece com crescimento infinito e os antigos com queda de 100%.
**Impacto:** Bloco 5 mostraria dados errados.
**Solução:** Função JavaScript genérica `buildAreaBaseline()` que detecta cursos que sumiram e usa o total deles como baseline para o curso novo na mesma área. Funciona para qualquer reclassificação futura.

### 8.3 OSRM — distância de carro vs. linha reta
**Problema:** Distância haversine não bate com Google Maps (linha reta vs. estrada).
**Impacto:** Vendedora reclamou que "todas as empresas aparecem perto demais".
**Solução:** OSRM `router.project-osrm.org/table/v1/driving` — gratuito, batch de 99 waypoints. Fallback para haversine se API falhar.

### 8.4 Encoding Windows + DuckDB
**Problema:** Caracteres acentuados (ç, ã, õ) saem como `?` no terminal Windows. DuckDB lê do Excel com problemas de styling do openpyxl.
**Impacto:** Output ilegível em prints, dificuldade de validação.
**Solução:**
- `sys.stdout.reconfigure(encoding='utf-8')` no início de cada script
- Em PowerShell: `$env:PYTHONIOENCODING="utf-8"`
- Filtrar `Select-String -NotMatch "UserWarning|openpyxl"` ao rodar via PowerShell

### 8.5 DuckDB file lock entre processos
**Problema:** Tentar abrir DuckDB em paralelo trava o arquivo. Background tasks Python ficavam pendurados.
**Impacto:** Workflow de iteração rápida quebrava.
**Solução:** Sempre fechar `con.close()` no final, e em caso de processos travados, identificar PID via `Get-Process python` e encerrar.

### 8.6 Porte Receita Federal — SPE problem
**Problema:** Porte 5 ("Demais") inclui empresas operacionais E SPEs/holdings com capital de R$ 1.000.
**Impacto:** Lista de "empresas grandes" inflada com casca de holdings.
**Solução:**
- Adicionar filtro de capital social mínimo (default R$ 500K)
- Dropdown de faixas para o usuário ajustar
- Label corrigido: não dizer "médias e grandes", dizer "porte 5 com capital > R$X"

### 8.7 INPC vs. IPCA — escolha de deflator
**Problema:** Atlas ADH usa valores de **2010**. RAIS usa de **2022**. Como deflacionar?
**Decisão:** IPCA (série BCB 433). Justificativa: produto consumido por classe média alta, IPCA-IBGE é o mais aceito como referência de cesta de consumo dessa faixa.

### 8.8 Score de Atratividade — anomalias industriais
**Problema:** Gavião Peixoto (Embraer), Paulínia (Petrobras) aparecem rank 2-3 com D1=100.
**Impacto:** Falso positivo — cidades minúsculas com salário médio inflado por uma planta industrial.
**Decisão:** **Não corrigir** — mostrar D1=100 mas D2=4 lado a lado. O usuário entende que é um caso especial. Forçar o usuário a pensar é melhor que esconder o dado.

### 8.9 Bug do template — placeholders `{{var}}` vs `{var}`
**Problema:** Template do prompt LLM usava `{{nome_municipio}}` (escape Python f-string) mas era processado com `.replace("{nome_municipio}", ...)` (single brace).
**Impacto:** Output ficava `{Campinas}` em vez de `Campinas`.
**Solução:** Padronizar para single brace em arquivos não-f-string.

### 8.10 .env vazado no git
**Problema:** `dashboard/.env` foi committed inicialmente com placeholder; quando colocamos chave real, ela seria pushed.
**Impacto:** Chave Anthropic poderia vazar publicamente.
**Solução:**
- `git rm --cached dashboard/.env`
- Confirmar `.env` em `.gitignore`
- Chave fica local; usuários do projeto criam o próprio `.env`

---

## 9. ESTATÍSTICAS DO PROJETO

### Linhas de código por categoria

| Categoria | Linhas |
|---|---|
| **dbt models (staging + facts + dimensions)** | 717 |
| ├─ Staging (9 modelos) | 469 |
| ├─ Facts (8 modelos) | 262 |
| └─ Dimensions (1 modelo) | 51 |
| **Scripts de validação (data/teste_b*.py)** | 1.075 |
| ├─ teste_b1.py (perfil socioeconômico) | 124 |
| ├─ teste_b23.py (mercado + tecido empresarial) | 119 |
| ├─ teste_b4.py (empresas-alvo) | 109 |
| ├─ teste_b5.py (pipeline universitário) | 194 |
| ├─ teste_b6.py (score de atratividade) | 202 |
| └─ teste_b7.py (narrativa LLM) | 217 + 137 (build_prompt) |
| **Previews HTML standalone (data/preview_b*.py)** | 1.599 |
| ├─ preview_b4.py | 352 |
| ├─ preview_b5.py | 471 |
| ├─ preview_b6.py | 473 |
| └─ preview_b7.py | 303 |
| **Backend FastAPI (dashboard/app.py + queries.py)** | 674 |
| **Frontend (dashboard/index.html)** | 755 |
| **Scripts auxiliares (ETL, diag, check)** | 396 |
| ├─ exportar_sp.py (BQ → DuckDB) | 102 |
| ├─ analisa_excels.py | 52 |
| ├─ build_prompt_b7.py | 137 |
| ├─ diag_*.py, check_*.py, read_excels.py | 105 |
| **TOTAL** | **5.216 linhas** |

### Volume de dados

| Tabela | Linhas | Observação |
|---|---|---|
| `dim_municipio` | 645 | Censo 2010, todos os municípios SP |
| `fct_empregos` | 13.216.062 | RAIS 2020-2024, granularidade alta |
| `fct_estabelecimentos` | 603.308 | RAIS estabs 2020-2024 |
| `fct_empresas` | 475.574 | CNPJ Receita, snapshot atual |
| `fct_mercado_superior` | 775.028 | INEP 2020-2024 |
| **Arquivo DuckDB total** | **311 MB** | |

### Bases externas integradas

- **Portfólio FGV:** 123 cursos ativos de MBA + Pós (excel `portfolio_fgv.xlsx`)
- **Cursos concorrentes:** 3.464 cursos brutos → 600 únicos após dedup (escola + curso) — 18 escolas: ESPM, FDC, IBMEC, INSPER, Mackenzie (4 unidades), MBA USP ESALQ, PUC Minas/Rio/SP/RS, Saint Paul (excel `portfolio_concorrentes.xlsx`)

### Modelos LLM

- **Modelo:** `claude-opus-4-7` (Anthropic)
- **Custo médio:** R$ 0,30 por análise completa
- **Tempo médio:** 15 segundos
- **Tokens médios:** 12.000 input + 4.500 output

---

## 10. PRÓXIMOS PASSOS

### Pendências para entrega final

1. **Consolidação no `dashboard/index.html`** com identidade visual FGV
   - Skin atual usa azul navy (#003770) + accent (#4A9FD4)
   - Aplicar tipografia oficial FGV
   - Logo no header
   - Footer institucional

2. **Reescrita de `dashboard/queries.py` para DuckDB local**
   - Substituir cliente BigQuery por `duckdb.connect("data/sp_mvp.duckdb")`
   - Remover `_run()` parametrizado BQ, usar f-strings (DuckDB local não tem injection risk)
   - Latência cai de 10s → 500ms

3. **Generalização para nacional**
   - Hoje filtrado para SP
   - Gerar arquivos DuckDB por UF
   - Frontend troca arquivo conforme UF selecionada

4. **Deploy em Cloud Run**
   - Container Docker com FastAPI + DuckDB embarcado
   - Volume mount para o arquivo DuckDB (refresh anual)
   - Domínio próprio (ex: `expansao.fgv.br`)

5. **Refresh anual do pipeline**
   - dbt: rodar staging + facts em cron job
   - Export DuckDB: rodar `exportar_sp.py` mensalmente

### Possíveis evoluções

- **Chatbot conversacional** com Claude para Q&A em cima dos dados ("E se o produto for graduação em vez de MBA?")
- **Comparador multi-cidade** — Campinas vs São José dos Campos vs Ribeirão Preto lado a lado
- **Mapa interativo** com cidades coloridas pelo score
- **Alertas automáticos** — quando cidade sobe ou cai significativamente no ranking
- **Integração com CRM FGV** — empresas-alvo do Bloco 4 viram leads pré-qualificados

---

## 11. COMO REPLICAR — GUIA PASSO A PASSO

### Pré-requisitos

- **Python 3.11+**
- **Conta Google Cloud** com acesso ao BigQuery
- **Conta Anthropic** para chave de API
- **dbt-bigquery** (`pip install dbt-bigquery`)
- Acesso ao `basedosdados.org` (público)

### Passo 1: Setup do BigQuery

```bash
# 1. Autenticar
gcloud auth application-default login

# 2. Criar projeto Google Cloud (ou usar existente)
gcloud projects create meu-projeto-fgv

# 3. Ativar BigQuery API no console
```

### Passo 2: dbt — Pipeline de transformação

```bash
# 1. Clonar este repo
git clone https://github.com/gabifgv/edu-expansion-intelligence.git
cd edu-expansion-intelligence

# 2. Configurar profiles.yml (BigQuery OAuth)
# Ajustar `profiles.yml` para seu projeto:
#   project: SEU-PROJETO-GCP
#   dataset: raw
#   location: US

# 3. Validar conexão
dbt debug

# 4. Rodar staging
dbt run --select staging

# 5. Rodar facts e dimensions
dbt run --select facts dimensions

# 6. Verificar
dbt test
```

### Passo 3: Export para DuckDB local

```bash
# Roda 1x — demora ~30 minutos para 13M linhas
python data/exportar_sp.py
# Cria data/sp_mvp.duckdb (~311 MB)
```

### Passo 4: Validar cada bloco

```bash
# Bloco 1 — perfil socioeconômico
python data/teste_b1.py

# Blocos 2+3 — mercado de trabalho + tecido empresarial
python data/teste_b23.py

# Bloco 4 — empresas-alvo
python data/teste_b4.py

# Bloco 5 — pipeline universitário
python data/teste_b5.py

# Bloco 6 — score de atratividade
python data/teste_b6.py
```

### Passo 5: Gerar previews HTML

```bash
python data/preview_b4.py  # → data/preview_b4.html
python data/preview_b5.py  # → data/preview_b5.html
python data/preview_b6.py  # → data/preview_b6.html
python data/preview_b7.py  # → data/preview_b7.html
```

Cada preview é um HTML autocontido. Abra direto no browser.

### Passo 6: Configurar Bloco 7 (Claude API)

```bash
# 1. Criar arquivo dashboard/.env
echo "ANTHROPIC_API_KEY=sk-ant-api03-SUA_CHAVE_AQUI" > dashboard/.env

# 2. Construir o prompt (carrega Excel files + monta template)
python data/build_prompt_b7.py
# → data/prompt_b7.json

# 3. Rodar análise para Campinas (gasta ~R$ 0,30)
python data/teste_b7.py
# → data/narrativa_campinas.txt

# 4. Re-gerar preview com narrativa real
python data/preview_b7.py
# → data/preview_b7.html (agora com narrativa pré-renderizada)
```

### Passo 7: Subir o dashboard FastAPI (versão atual com BigQuery)

```bash
cd dashboard
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
# Abrir http://localhost:8000
```

### Adaptação para outra UF

Para rodar com **MG** em vez de SP:
1. No `data/exportar_sp.py`, mudar `WHERE sigla_uf = 'SP'` para `'MG'` e renomear arquivo de saída
2. Nos scripts `teste_b*.py`, ajustar `id_municipio` default
3. Re-validar — algumas cidades menores podem ter dados esparsos

---

## 12. ANEXOS

### A. Estrutura de arquivos do repositório

```
edu-expansion-intelligence/
├── CLAUDE.md                          # guia para Claude Code (assistente)
├── README.md                          # readme do GitHub
├── DOCUMENTACAO_PROJETO.md            # ESTE DOCUMENTO
├── dbt_project.yml                    # config dbt
├── profiles.yml                       # credenciais BigQuery (OAuth)
│
├── models/                            # transformações dbt
│   ├── staging/                       # views (9 arquivos)
│   ├── facts/                         # tables (8 arquivos)
│   └── dimensions/                    # tables (1 arquivo)
│
├── dashboard/                         # aplicação web
│   ├── app.py                         # FastAPI (155 linhas)
│   ├── queries.py                     # queries BigQuery (519 linhas)
│   ├── index.html                     # frontend (755 linhas)
│   ├── requirements.txt               # deps Python
│   └── .env                           # API key (gitignored)
│
├── data/                              # validação e dados
│   ├── sp_mvp.duckdb                  # banco local (311 MB, gitignored)
│   ├── exportar_sp.py                 # ETL BQ → DuckDB
│   │
│   ├── teste_b1.py                    # validação Bloco 1
│   ├── teste_b23.py                   # validação Blocos 2+3
│   ├── teste_b4.py                    # validação Bloco 4
│   ├── teste_b5.py                    # validação Bloco 5
│   ├── teste_b6.py                    # validação Bloco 6
│   ├── teste_b7.py                    # validação Bloco 7 (LLM)
│   │
│   ├── preview_b4.py / .html          # protótipo Bloco 4
│   ├── preview_b5.py / .html          # protótipo Bloco 5
│   ├── preview_b6.py / .html          # protótipo Bloco 6
│   ├── preview_b7.py / .html          # protótipo Bloco 7
│   │
│   ├── build_prompt_b7.py             # constrói prompt Claude
│   ├── prompt_b7.json                 # template SYSTEM + USER
│   ├── narrativa_campinas.txt         # output Claude para Campinas
│   │
│   ├── portfolio_fgv.xlsx             # 123 cursos FGV
│   ├── portfolio_concorrentes.xlsx    # 3.464 cursos concorrentes
│   ├── fgv-depara.xlsx                # NÃO usado no MVP MBA/Pós
│   │
│   └── analisa_excels.py / diag_*.py / check_*.py / read_excels.py
│       └── scripts auxiliares de exploração
│
└── .gitignore                         # protege .env, *.duckdb, __pycache__
```

### B. Tabela-resumo dos 7 blocos

| Bloco | O que mostra | Por que importa | Validação |
|---|---|---|---|
| 1. Perfil Socioeconômico | Cidade vs UF em IDHM, renda, escolaridade | Define maturidade do mercado | `teste_b1.py` |
| 2+3. Mercado + Tecido Empresarial | Setores e cargos com elegíveis | Onde focar prospecção | `teste_b23.py` |
| 4. Empresas-Alvo | CNPJ + contato + distância de carro | Leads B2B prontos | `teste_b4.py` + `preview_b4.html` |
| 5. Pipeline Universitário | Concluintes por área, IES locais | Pipeline de demanda futura | `teste_b5.py` + `preview_b5.html` |
| 6. Score de Atratividade | 0-100 com 4 dimensões ajustáveis | Comparação inter-municípios | `teste_b6.py` + `preview_b6.html` |
| 7. Narrativa AI | Relatório 6 seções via Claude | Síntese executiva acionável | `teste_b7.py` + `preview_b7.html` |

### C. Glossário

- **Elegível:** vínculo formal RAIS com `salario_medio_reais >= renda_mínima` (mensalidade ÷ % renda)
- **Renda mínima:** `mensalidade ÷ (% renda destinada à educação)` — ex: R$ 1.200 ÷ 30% = R$ 4.000
- **% elegíveis:** vínculos elegíveis ÷ total de vínculos formais
- **Subsetor IBGE:** 25 categorias (Comércio, Ensino, Indústria Química, etc.)
- **Porte 5 (Receita):** "Demais" — médias e grandes empresas. Pode incluir SPEs/holdings (filtrar por capital social)
- **CNAE classe:** 4 dígitos (vs. 7 dígitos da subclasse). Nível de classificação setorial
- **Área detalhada (INEP):** classificação CINE Brasil, mais granular que área geral
- **Concluintes:** alunos que terminaram o curso no ano de referência
- **D1-D4:** 4 dimensões do score (Capacidade Pagamento, Tamanho Mercado, Pipeline, Dinamismo)
- **Min-max normalization:** `(x - min) / (max - min)` — padroniza para [0, 1] dentro do estado

### D. Referências de fontes

- **basedosdados.org** — dados públicos brasileiros no BigQuery
- **API BCB série 433** — IPCA mensal (deflator)
- **OSRM** — `router.project-osrm.org` (distância de carro)
- **BrasilAPI CEP v2** — `brasilapi.com.br/api/cep/v2/{cep}`
- **Anthropic API** — `console.anthropic.com`

### E. Comandos úteis

```bash
# Verificar tamanho do DuckDB
du -sh data/sp_mvp.duckdb

# Listar tabelas e contar linhas
python -c "import duckdb; c=duckdb.connect('data/sp_mvp.duckdb'); print(c.execute('SELECT table_name, estimated_size FROM duckdb_tables()').df())"

# Re-rodar dbt parcialmente
dbt run --select staging.stg_rais_vinculos_municipio
dbt run --select facts.fct_empregos

# Limpar __pycache__
find . -name __pycache__ -type d -exec rm -rf {} +

# Push para GitHub
git add -A && git commit -m "msg" && git push origin main
```

---

## CRÉDITOS

**Desenvolvido por:** Gabriella do Nascimento Pinheiro (TCC MBA FGV)
**Co-development com IA:** Claude (Anthropic) — pair programming via Claude Code CLI
**Modelos LLM utilizados em desenvolvimento:** Claude Sonnet 4.6 + Opus 4.7
**Modelo LLM em produção:** `claude-opus-4-7`
**Cliente interno:** Time de Expansão FGV (escolas de MBA e Pós-Graduação)

**Tecnologias:**
- BigQuery + dbt-bigquery
- DuckDB
- FastAPI + Pydantic
- HTML5 + Vanilla JS + Plotly.js
- Anthropic Claude API
- BrasilAPI, OSRM, BCB API

**Repositório:** `https://github.com/gabifgv/edu-expansion-intelligence`

---

*Documento gerado em maio/2026 ao final do ciclo de validação dos 7 blocos.*
*Última atualização: commit `541dd66` — "Validação dos 7 blocos do dashboard FGV: scripts DuckDB + previews HTML + LLM"*
