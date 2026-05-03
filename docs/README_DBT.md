# DBT - Inteligência de Expansão Educacional

Projeto dbt para o TCC sobre Inteligência de Expansão Educacional. Esta estrutura segue as melhores práticas de organização de camadas de transformação de dados.

## Estrutura do Projeto

```
projeto/
├── models/
│   ├── raw/              # Camada de dados brutos
│   ├── staging/          # Camada de transformação inicial
│   └── marts/            # Camada de modelos analíticos
├── tests/                # Testes de qualidade de dados
├── data/                 # Dados estáticos (seeds)
├── macros/               # Macros reutilizáveis
├── analyses/             # Análises ad-hoc
├── docs/                 # Documentação
├── dbt_project.yml       # Configuração principal do projeto
└── profiles.yml          # Credenciais de conexão
```

## Camadas de Dados

### Raw (Bruto)
- Fontes de dados originais
- Views sobre tabelas primárias
- Limpeza mínima

### Staging (Preparação)
- Transformações iniciais
- Validação de dados
- Normalização de tipos
- Renomeação de colunas

### Marts (Analítico)
- Tabelas agregadas e dimensionais
- Pronto para BI/Relatórios
- KPIs e métricas calculadas

## Configuração

1. **Editar `profiles.yml`**: Adicionar credenciais do banco de dados
2. **Executar `dbt init`**: Inicializar o projeto (se necesário)
3. **Executar `dbt deps`**: Instalar dependências

## Comandos Úteis

```bash
dbt debug                 # Testar conexão
dbt run                   # Executar models
dbt test                  # Executar testes
dbt docs generate         # Gerar documentação
dbt docs serve            # Servir documentação localmente
dbt run --select raw      # Executar apenas raw
```

## Nomeclatura de Arquivos

- `stg_[fonte]_[entidade].sql` - Staging models
- `dim_[dimensão].sql` - Tabelas de dimensão
- `fact_[fato].sql` - Tabelas de fatos
- `fct_[fato].sql` - Tabelas de fatos (alternativo)

## Referências

- [Documentação dbt](https://docs.getdbt.com/)
- [Melhores Práticas](https://docs.getdbt.com/guides/best-practices)
