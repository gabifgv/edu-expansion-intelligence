import duckdb, sys, os, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# ── Chave API ─────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / "dashboard" / ".env"
for line in env_path.read_text().splitlines():
    if line.startswith("ANTHROPIC_API_KEY="):
        os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()

try:
    import anthropic
    client = anthropic.Anthropic()
    API_OK = not os.environ["ANTHROPIC_API_KEY"].startswith("sk-ant-v0-placeholder")
except Exception as e:
    print(f"[AVISO] {e}"); API_OK = False

# ── Parâmetros (simulam os filtros do usuário no dashboard) ───────────────────
ID_MUN      = "3509502"   # Campinas
SIGLA_UF    = "SP"
PRODUTO     = "MBA Executivo"
MENSALIDADE = 1200        # R$/mês
PCT_RENDA   = 30          # % da renda destinada à educação
RENDA_MIN   = round(MENSALIDADE / (PCT_RENDA / 100))   # R$ 4.000

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")
ANO_EMP = con.execute("SELECT MAX(ano) FROM fct_empregos").fetchone()[0]

# ── Bloco 1: Perfil socioeconômico ────────────────────────────────────────────
b1 = con.execute(f"""
    SELECT nome_municipio, populacao_total, idhm, idhm_educacao, idhm_renda,
           renda_per_capita, indice_gini, taxa_superior_25_mais,
           prop_pobreza, populacao_18_24
    FROM dim_municipio WHERE id_municipio = '{ID_MUN}'
""").fetchone()
(nome_mun, pop, idhm, idhm_educ, idhm_renda, renda_pc,
 gini, taxa_sup, pobreza, pop_18_24) = b1

DADOS_B1 = f"""Município: {nome_mun} | Pop. total: {int(pop):,} hab | Pop. 18-24 anos: {int(pop_18_24):,}
IDHM: {idhm:.3f} (educação: {idhm_educ:.3f} | renda: {idhm_renda:.3f})
Renda per capita: R$ {renda_pc:,.0f}/ano | Gini: {gini:.3f} | Proporção em pobreza: {pobreza:.1f}%
% população 25+ com ensino superior: {taxa_sup:.1f}%"""

# ── Bloco 2+3: Mercado de trabalho ────────────────────────────────────────────
emp_tot = con.execute(f"""
    SELECT SUM(total_vinculos) v,
           SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos ELSE 0 END) e,
           SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos*salario_medio_reais ELSE 0 END)
               / NULLIF(SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos ELSE 0 END),0) sal_e
    FROM fct_empregos WHERE id_municipio = '{ID_MUN}' AND ano = {ANO_EMP}
""").fetchone()
vinculos, eleg, sal_eleg = emp_tot

top_set = con.execute(f"""
    SELECT descricao_subsetor, SUM(total_vinculos) v,
           SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos ELSE 0 END) e
    FROM fct_empregos
    WHERE id_municipio = '{ID_MUN}' AND ano = {ANO_EMP} AND descricao_subsetor IS NOT NULL
    GROUP BY 1 ORDER BY 3 DESC LIMIT 6
""").df()

top_cargo = con.execute(f"""
    SELECT descricao_cargo, SUM(total_vinculos) v,
           SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos ELSE 0 END) e,
           SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos*salario_medio_reais ELSE 0 END)
               / NULLIF(SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos ELSE 0 END),0) sal
    FROM fct_empregos
    WHERE id_municipio = '{ID_MUN}' AND ano = {ANO_EMP} AND descricao_cargo IS NOT NULL
    GROUP BY 1 ORDER BY 3 DESC LIMIT 8
""").df()

set_str = "\n".join(
    f"  {r['descricao_subsetor']}: {int(r['v']):,} vínculos | {int(r['e']):,} elegíveis"
    for _, r in top_set.iterrows()
)
cargo_str = "\n".join(
    f"  {r['descricao_cargo']}: {int(r['e']):,} eleg. | sal. médio eleg. R$ {r['sal']:,.0f}"
    for _, r in top_cargo.iterrows() if r['e'] > 0
)

DADOS_B23 = f"""Vínculos formais totais: {int(vinculos):,} | Elegíveis (sal ≥ R${RENDA_MIN:,}): {int(eleg):,} ({eleg/vinculos*100:.1f}%)
Salário médio dos elegíveis: R$ {sal_eleg:,.0f}/mês

Top 6 setores por elegíveis:
{set_str}

Top 8 cargos por elegíveis:
{cargo_str}"""

# ── Bloco 4: Empresas-alvo (top 5 por capital social — sem OSRM no teste) ────
emp5 = con.execute(f"""
    WITH sl AS (
        SELECT cnae_classe, descricao_subsetor, SUM(total_vinculos) v
        FROM fct_empregos WHERE cnae_classe IS NOT NULL GROUP BY 1,2
    ),
    slookup AS (SELECT DISTINCT ON (cnae_classe) cnae_classe, descricao_subsetor
                FROM sl ORDER BY cnae_classe, v DESC)
    SELECT e.nome_empresa, COALESCE(sl.descricao_subsetor,'Não classificado') setor,
           e.capital_social, e.cep
    FROM fct_empresas e
    LEFT JOIN slookup sl ON sl.cnae_classe = e.cnae_classe
    WHERE e.id_municipio = '{ID_MUN}' AND e.porte = '5' AND e.capital_social >= 1000000
    ORDER BY e.capital_social DESC LIMIT 5
""").df()

emp_str = "\n".join(
    f"  {r['nome_empresa']} | Setor: {r['setor']} | Capital social: R$ {r['capital_social']:,.0f}"
    for _, r in emp5.iterrows()
)

DADOS_B4 = f"Top 5 empresas de grande porte (capital > R$1M):\n{emp_str}"

# ── Bloco 5: Pipeline universitário ──────────────────────────────────────────
sup = con.execute(f"""
    SELECT SUM(CASE WHEN ano=2024 THEN total_concluintes ELSE 0 END) c24,
           SUM(CASE WHEN ano=2023 THEN total_concluintes ELSE 0 END) c23,
           SUM(CASE WHEN ano=2020 THEN total_concluintes ELSE 0 END) c20,
           COUNT(DISTINCT CASE WHEN ano=2024 THEN id_ies END) ies24
    FROM fct_mercado_superior WHERE id_municipio = '{ID_MUN}'
""").fetchone()
c24, c23, c20, ies24 = sup
d23 = (c24-c23)/c23*100 if c23 else 0
d20 = (c24-c20)/c20*100 if c20 else 0

top_ies = con.execute(f"""
    SELECT nome_ies, rede, SUM(total_concluintes) conc
    FROM fct_mercado_superior
    WHERE id_municipio = '{ID_MUN}' AND ano = 2024
    GROUP BY 1,2 ORDER BY 3 DESC LIMIT 5
""").df()

cursos_alta = con.execute(f"""
    WITH agg AS (
        SELECT nome_area_detalhada,
               SUM(CASE WHEN ano=2024 THEN total_concluintes ELSE 0 END) c24,
               SUM(CASE WHEN ano=2020 THEN total_concluintes ELSE 0 END) c20
        FROM fct_mercado_superior WHERE id_municipio = '{ID_MUN}' GROUP BY 1
    )
    SELECT nome_area_detalhada, c24, ROUND((c24-c20)/NULLIF(c20,0)*100,1) cresc
    FROM agg WHERE c24 >= 200 AND c20 > 0 AND c24 > c20
    ORDER BY (c24/1000.0)*((c24-c20)/NULLIF(c20,0)) DESC LIMIT 6
""").df()

ies_str = "\n".join(
    f"  {r['nome_ies']} ({r['rede']}): {int(r['conc']):,} conc."
    for _, r in top_ies.iterrows()
)
alta_str = "\n".join(
    f"  {r['nome_area_detalhada']}: {int(r['c24']):,} conc. em 2024 ({float(r['cresc']):+.0f}% vs 2020)"
    for _, r in cursos_alta.iterrows()
)

DADOS_B5 = f"""Concluintes 2024: {int(c24):,} | IES: {int(ies24)} | vs 2023: {d23:+.1f}% | vs 2020: {d20:+.1f}%

Top 5 IES por volume de formandos (2024):
{ies_str}

Cursos em alta — maior volume + crescimento 2020→2024:
{alta_str}"""

con.close()

# ── Bloco 6: score ────────────────────────────────────────────────────────────
D1, D2, D3, D4 = 57, 12, 59, 48
SCORE = round(0.35*(D1/100) + 0.30*(D2/100) + 0.20*(D3/100) + 0.15*(D4/100), 3) * 100

# ── Carrega template do prompt ────────────────────────────────────────────────
prompt_data = json.loads(Path("data/prompt_b7.json").read_text(encoding='utf-8'))
SYSTEM = prompt_data["system"]
template = prompt_data["user_template"]

USER = (template
    .replace("{nome_municipio}", nome_mun)
    .replace("{sigla_uf}", SIGLA_UF)
    .replace("{produto}", PRODUTO)
    .replace("{mensalidade}", f"{MENSALIDADE:,}")
    .replace("{renda_min}", f"{RENDA_MIN:,}")
    .replace("{pct_renda}", str(PCT_RENDA))
    .replace("{ano_emp}", str(ANO_EMP))
    .replace("{dados_b1}", DADOS_B1)
    .replace("{dados_b23}", DADOS_B23)
    .replace("{dados_b4}", DADOS_B4)
    .replace("{dados_b5}", DADOS_B5)
    .replace("{score}", f"{SCORE:.1f}")
    .replace("{rank}", "4")
    .replace("{n_mun}", "645")
    .replace("{D1}", str(D1))
    .replace("{D2}", str(D2))
    .replace("{D3}", str(D3))
    .replace("{D4}", str(D4))
)

print("=== CONTEXTO COMPLETO ENVIADO AO CLAUDE ===")
print(USER[:2000], "\n...[truncado para exibição]")
print(f"\n[Tamanho total do prompt: {len(USER)} chars | ~{len(USER)//4} tokens estimados]")

if not API_OK:
    print("\n[AVISO] Configure a chave real em dashboard/.env para gerar a narrativa.")
    print("Prompt salvo e pronto para uso assim que a chave for inserida.")
    sys.exit(0)

# ── Chama Claude API ──────────────────────────────────────────────────────────
print("\n=== GERANDO NARRATIVA COM CLAUDE ===\n")
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=4500,
    system=SYSTEM,
    messages=[{"role": "user", "content": USER}]
)

narrativa = response.content[0].text
print(narrativa)
print(f"\n[tokens: input={response.usage.input_tokens} | output={response.usage.output_tokens}]")

Path("data/narrativa_campinas.txt").write_text(narrativa, encoding="utf-8")
print("[Narrativa salva em data/narrativa_campinas.txt]")
