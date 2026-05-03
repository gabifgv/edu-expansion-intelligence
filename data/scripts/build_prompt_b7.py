"""
Monta SYSTEM + USER prompt do Bloco 7.
Regras:
- fgv-depara NÃO é usado
- Concorrentes: nome da escola + nome do curso, sem distinção geográfica
- Propósito concorrentes: identificar cursos que concorrentes têm e FGV não tem
- Match obrigatório: setor elegível + curso de graduação em alta → recomendação de pós
"""
import pandas as pd, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# ── Portfólio FGV (limpa metadados) ──────────────────────────────────────────
fgv_raw = pd.read_excel('data/portfolio_fgv.xlsx')
cursos_fgv = [
    str(c).strip() for c in fgv_raw['Curso']
    if pd.notna(c) and str(c).strip()
    and not any(kw in str(c) for kw in ['Filtros', 'Unifica', 'DataFim', 'Curso não'])
]
PORTFOLIO_FGV = "\n".join(f"  - {c}" for c in cursos_fgv)

# ── Concorrentes: escola + curso, sem filtro geográfico, sem duplicatas ───────
conc_raw = pd.read_excel('data/portfolio_concorrentes.xlsx')
conc_clean = (
    conc_raw[['Escola', 'Curso']]
    .dropna()
    .drop_duplicates(subset=['Escola', 'Curso'])
    .sort_values(['Escola', 'Curso'])
)
# Remove FGV da lista de concorrentes (não faz sentido comparar FGV com FGV)
conc_clean = conc_clean[conc_clean['Escola'] != 'FGV']

CONCORRENTES_LIST = "\n".join(
    f"  {r['Escola']} | {r['Curso']}"
    for _, r in conc_clean.iterrows()
)
n_conc = len(conc_clean)
escolas_unicas = sorted(conc_clean['Escola'].unique())

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Você é especialista sênior em pesquisa e análise de mercado para portfólio de MBA e "
    "pós-graduação da Fundação Getulio Vargas (FGV). "
    "Seu público é o Diretor de Expansão, que lê para decidir — não para se informar genericamente. "
    "Escreva com autoridade analítica: cite números dos dados fornecidos, não use introduções genéricas, "
    "cada seção abre direto no insight. "
    "Tom executivo, parágrafos densos de 4 a 6 linhas. "
    "Quando citar empresas e IES, use os nomes exatos fornecidos nos dados. "
    "Nunca invente dados — use apenas o que está no contexto fornecido."
)

# ── User prompt template ──────────────────────────────────────────────────────
USER_PROMPT_TEMPLATE = (
"""Analise os dados abaixo de {nome_municipio}/{sigla_uf} e produza relatório executivo de inteligência de mercado para o portfólio FGV.
Produto: "{produto}" | Mensalidade: R$ {mensalidade}/mês | Renda mínima estimada: R$ {renda_min}/mês ({pct_renda}% da renda do elegível)

══════════════════════════════════════════════
BLOCO 1 — PERFIL SOCIOECONÔMICO
{dados_b1}

BLOCO 2+3 — MERCADO DE TRABALHO FORMAL ({ano_emp})
{dados_b23}

BLOCO 4 — EMPRESAS-ALVO (top 5 por capital social, porte grande, capital > R$1M)
{dados_b4}

BLOCO 5 — PIPELINE UNIVERSITÁRIO (formandos por área/curso)
{dados_b5}

BLOCO 6 — SCORE DE ATRATIVIDADE: {score}/100 — Rank #{rank} em {sigla_uf} ({n_mun} municípios)
D1 Cap. Pagamento: {D1}/100 | D2 Tam. Mercado: {D2}/100 | D3 Pipeline Acadêmico: {D3}/100 | D4 Dinamismo: {D4}/100
══════════════════════════════════════════════

PORTFÓLIO FGV ATIVO — MBA E PÓS-GRADUAÇÃO ("""
+ str(len(cursos_fgv))
+ """ cursos):
"""
+ PORTFOLIO_FGV
+ """

══════════════════════════════════════════════
CURSOS DE CONCORRENTES NO MERCADO ("""
+ str(n_conc)
+ """ cursos únicos de: """
+ ", ".join(escolas_unicas)
+ """):
Instruções de uso desta lista:
- Compare com o Portfólio FGV acima
- Se identificar curso de concorrente com alta aderência ao mercado local E sem equivalente FGV, cite-o na seção "Cursos Recomendados" como lacuna de portfólio
- Não faça distinção geográfica — considere todos os cursos como referência de mercado

"""
+ CONCORRENTES_LIST
+ """

══════════════════════════════════════════════
Produza o relatório com EXATAMENTE estas 6 seções, nesta ordem:

**1. Perfil da Cidade**
Disserte sobre o perfil socioeconômico de {nome_municipio}: o que IDHM, renda, escolaridade e a composição do mercado de trabalho revelam sobre a maturidade e o tamanho do mercado para MBA/Pós FGV nessa praça. Cite os números.

**2. Mercado de Trabalho**
Analise os setores e cargos com maior concentração de elegíveis. Qual o ticket realista considerando o salário médio dos elegíveis e a mensalidade de R$ {mensalidade}/mês? Onde está a maior demanda latente por educação executiva?

**3. Cursos Recomendados**
Esta é a seção mais importante. Faça o cruzamento em três camadas:
CAMADA 1 — Setor → Pós: Para os setores dominantes (Bloco 2+3), qual pós-graduação é mais procurada por profissionais desse setor? Cite os nomes exatos do portfólio FGV com fit imediato.
CAMADA 2 — Graduação → Pós: Para os cursos de graduação com mais formandos (Bloco 5), qual é a progressão natural para MBA ou pós? Exemplo: formandos em Administração buscam MBA em Gestão; formandos em TI buscam MBA em Transformação Digital. Use os dados de cursos em alta (Bloco 5) para priorizar.
CAMADA 3 — Gaps de portfólio: Se identificar curso de concorrente com alta aderência ao mercado local e sem equivalente FGV, cite o nome exato (escola + curso) e proponha o tema que a FGV deveria desenvolver.

**4. Prospecção Corporativa**
Cite pelo menos 3 empresas do Bloco 4 pelo nome exato. Para cada uma: setor, por que é prioritária para turma fechada ou parceria B2B, modelo de abordagem sugerido. Seja específico e acionável.

**5. Parcerias Acadêmicas**
Com base nas IES do Bloco 5, indique as 3 mais estratégicas para parceria de captação (pipeline de formandos, co-marketing, turmas fechadas). Justifique com o dado concreto — volume de formandos e área de força da IES.

**6. Veredito Estratégico**
Avalie objetivamente se {nome_municipio} é uma boa estratégia de expansão para a FGV no produto "{produto}". Atribua prioridade: **Alta**, **Média** ou **Baixa**. Justifique com os 2-3 fatores mais decisivos. Seja direto — este parágrafo define a ação."""
)

# ── Salva ─────────────────────────────────────────────────────────────────────
payload = {
    "system": SYSTEM_PROMPT,
    "user_template": USER_PROMPT_TEMPLATE,
    "portfolio_fgv_count": len(cursos_fgv),
    "concorrentes_count": n_conc,
    "escolas_concorrentes": escolas_unicas,
}
Path("data/prompt_b7.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8'
)

print(f"Portfolio FGV: {len(cursos_fgv)} cursos")
print(f"Concorrentes: {n_conc} cursos únicos de {len(escolas_unicas)} escolas")
print(f"Escolas: {', '.join(escolas_unicas)}")
print(f"Tamanho estimado do prompt: ~{len(USER_PROMPT_TEMPLATE)//4} tokens (template)")
print("Prompt salvo: data/prompt_b7.json")
