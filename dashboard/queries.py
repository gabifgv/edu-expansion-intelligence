from google.cloud import bigquery
import pandas as pd

PROJECT = "project-a8f8452a-3033-4dd8-99a"
_client = None


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT)
    return _client


def _run(sql: str, params: dict | None = None) -> pd.DataFrame:
    client = get_client()
    if params:
        def _bq_param(k, v):
            if isinstance(v, float):
                return bigquery.ScalarQueryParameter(k, "FLOAT64", v)
            if isinstance(v, int):
                return bigquery.ScalarQueryParameter(k, "INT64", v)
            return bigquery.ScalarQueryParameter(k, "STRING", str(v))

        job_config = bigquery.QueryJobConfig(
            query_parameters=[_bq_param(k, v) for k, v in params.items()]
        )
        return client.query(sql, job_config=job_config).to_dataframe()
    return client.query(sql).to_dataframe()


# ─────────────────────────────────────────
# Listagem de UFs e municípios para filtros
# ─────────────────────────────────────────

def get_ufs() -> list[str]:
    df = _run("""
        SELECT DISTINCT sigla_uf
        FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
        ORDER BY sigla_uf
    """)
    return df["sigla_uf"].tolist()


def get_municipios(sigla_uf: str) -> list[dict]:
    df = _run("""
        SELECT id_municipio, nome_municipio
        FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
        WHERE sigla_uf = @uf
        ORDER BY nome_municipio
    """, {"uf": sigla_uf})
    return df.to_dict(orient="records")


# ─────────────────────────────────────────
# BLOCO 1 — Perfil socioeconômico
# cidade + média da UF
# ─────────────────────────────────────────

def get_perfil_socioeconomico(id_municipio: str, sigla_uf: str) -> dict:
    cidade_df = _run("""
        SELECT nome_municipio, sigla_uf, idhm, renda_per_capita, indice_gini,
               populacao_total, populacao_urbana, taxa_superior_25_mais, prop_pobreza
        FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
        WHERE id_municipio = @municipio
    """, {"municipio": id_municipio})

    uf_df = _run("""
        SELECT
            ROUND(AVG(idhm), 3)                   AS idhm,
            ROUND(AVG(renda_per_capita), 2)        AS renda_per_capita,
            ROUND(AVG(indice_gini), 3)             AS indice_gini,
            ROUND(AVG(populacao_total), 0)         AS populacao_total,
            ROUND(AVG(populacao_urbana), 0)        AS populacao_urbana,
            ROUND(AVG(taxa_superior_25_mais), 2)   AS taxa_superior_25_mais,
            ROUND(AVG(prop_pobreza), 2)            AS prop_pobreza
        FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
        WHERE sigla_uf = @uf
    """, {"uf": sigla_uf})

    cidade = cidade_df.iloc[0].to_dict() if len(cidade_df) else {}
    uf_avg = uf_df.iloc[0].to_dict() if len(uf_df) else {}

    metrics = [
        ("taxa_superior_25_mais", "Pop. 25+ com superior completo (%)", True),
        ("renda_per_capita",      "Renda per capita (R$)",              True),
        ("idhm",                  "IDHM geral",                         True),
        ("indice_gini",           "Índice de Gini (desigualdade)",       False),  # maior = pior
        ("populacao_total",       "População total",                     None),   # neutro
        ("populacao_urbana",      "População urbana",                    None),
        ("prop_pobreza",          "Proporção em pobreza (%)",            False),
    ]

    rows = []
    for col, label, higher_is_better in metrics:
        c_val = cidade.get(col)
        u_val = uf_avg.get(col)
        delta_pct = None
        if c_val and u_val and u_val != 0:
            delta_pct = round((c_val - u_val) / abs(u_val) * 100, 1)

        if delta_pct is None or higher_is_better is None:
            status = "neutro"
        elif higher_is_better:
            status = "acima" if delta_pct > 0 else "abaixo"
        else:
            status = "acima" if delta_pct < 0 else "abaixo"  # invertido: menor Gini = melhor

        rows.append({
            "metrica": label,
            "cidade": c_val,
            "uf_media": u_val,
            "delta_pct": delta_pct,
            "status": status,
        })

    return {
        "nome_municipio": cidade.get("nome_municipio", ""),
        "sigla_uf": sigla_uf,
        "rows": rows,
    }


# ─────────────────────────────────────────
# BLOCO 2 — Vínculos formais (RAIS)
# ─────────────────────────────────────────

def get_vinculos(id_municipio: str, sigla_uf: str, renda_minima: float, ano: int = 2022) -> dict:
    # Vínculos do município com enriquecimento de cnae via diretório
    df = _run(f"""
        WITH vinculos AS (
            SELECT
                e.descricao_subsetor,
                COALESCE(e.descricao_cnae, cn.descricao) AS descricao_cnae,
                e.cnae_2,
                e.cbo_2002,
                e.descricao_cargo,
                e.total_vinculos,
                e.salario_medio_reais,
                e.salario_medio_sm
            FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos` e
            LEFT JOIN `basedosdados.br_bd_diretorios_brasil.cnae_2` cn
                ON LPAD(e.cnae_2, 5, '0') = cn.classe
            WHERE e.id_municipio = @municipio
              AND e.ano = {ano}
        )
        SELECT *,
            (salario_medio_reais >= @renda_min) AS elegivel
        FROM vinculos
        ORDER BY salario_medio_reais DESC
    """, {"municipio": id_municipio, "renda_min": renda_minima})

    # Série histórica de vínculos elegíveis (anos com dados completos)
    trend_df = _run("""
        SELECT ano,
               SUM(total_vinculos) AS total_vinculos,
               SUM(CASE WHEN salario_medio_reais >= @renda_min THEN total_vinculos ELSE 0 END) AS vinculos_elegiveis
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
        WHERE id_municipio = @municipio
          AND ano IN (2020, 2021, 2022)
        GROUP BY ano ORDER BY ano
    """, {"municipio": id_municipio, "renda_min": renda_minima})

    # Mesmo threshold mas para a UF (para contexto)
    uf_total = _run(f"""
        SELECT SUM(CASE WHEN salario_medio_reais >= @renda_min THEN total_vinculos ELSE 0 END) AS uf_elegiveis
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
        WHERE sigla_uf = @uf AND ano = {ano}
    """, {"uf": sigla_uf, "renda_min": renda_minima})

    return {
        "ano": ano,
        "renda_minima": renda_minima,
        "rows": df.to_dict(orient="records"),
        "total_elegiveis": int(df[df["elegivel"] == True]["total_vinculos"].sum()) if len(df) else 0,
        "total_vinculos": int(df["total_vinculos"].sum()) if len(df) else 0,
        "uf_elegiveis": int(uf_total.iloc[0]["uf_elegiveis"]) if len(uf_total) else 0,
        "trend": trend_df.to_dict(orient="records"),
    }


# ─────────────────────────────────────────
# BLOCO 3 — Densidade empresarial
# ─────────────────────────────────────────

def get_estabelecimentos(id_municipio: str, renda_minima: float, ano: int = 2023) -> dict:
    # Estabelecimentos com % elegível calculado via join com vinculos 2022
    df = _run(f"""
        WITH estab AS (
            SELECT descricao_subsetor, descricao_cnae, cnae_2,
                   SUM(total_estabelecimentos) AS total_estabelecimentos,
                   SUM(total_vinculos_ativos)  AS total_vinculos_ativos
            FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_estabelecimentos`
            WHERE id_municipio = @municipio AND ano = {ano}
            GROUP BY 1, 2, 3
        ),
        vinc AS (
            SELECT COALESCE(cnae_2, '') AS cnae_2,
                   SUM(total_vinculos) AS total_vinculos,
                   SUM(CASE WHEN salario_medio_reais >= @renda_min THEN total_vinculos ELSE 0 END) AS vinculos_elegiveis
            FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
            WHERE id_municipio = @municipio AND ano = 2022
            GROUP BY 1
        )
        SELECT
            e.descricao_subsetor,
            e.descricao_cnae,
            e.cnae_2,
            e.total_estabelecimentos,
            e.total_vinculos_ativos,
            COALESCE(v.vinculos_elegiveis, 0) AS vinculos_elegiveis,
            COALESCE(v.total_vinculos, 0)     AS vinculos_total_rais,
            ROUND(
                SAFE_DIVIDE(COALESCE(v.vinculos_elegiveis, 0),
                            NULLIF(COALESCE(v.total_vinculos, 0), 0)) * 100, 1
            ) AS pct_elegivel
        FROM estab e
        LEFT JOIN vinc v USING (cnae_2)
        ORDER BY e.total_estabelecimentos DESC
    """, {"municipio": id_municipio, "renda_min": renda_minima})

    return {
        "ano_estab": ano,
        "rows": df.to_dict(orient="records"),
        "total_estabelecimentos": int(df["total_estabelecimentos"].sum()) if len(df) else 0,
    }


# ─────────────────────────────────────────
# BLOCO 4 — Empresas-alvo (CNPJ)
# ─────────────────────────────────────────

def get_empresas(
    id_municipio: str,
    renda_minima: float,
    lat_polo: float | None = None,
    lon_polo: float | None = None,
) -> dict:
    # CNAEs com vinculos elegíveis (2022)
    cnae_df = _run("""
        SELECT DISTINCT cnae_2
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
        WHERE id_municipio = @municipio
          AND ano = 2022
          AND salario_medio_reais >= @renda_min
    """, {"municipio": id_municipio, "renda_min": renda_minima})

    if len(cnae_df) == 0:
        return {"rows": [], "total": 0}

    # IN list de CNAEs com espaços (máx 500)
    cnae_list = cnae_df["cnae_2"].dropna().tolist()[:500]
    cnae_in = ", ".join(f"'{c}'" for c in cnae_list)

    # Geocodificação embutida via haversine se tiver polo
    if lat_polo is not None and lon_polo is not None:
        dist_expr = f"""
            ROUND(
              6371 * ACOS(
                COS(RADIANS({lat_polo})) * COS(RADIANS(CAST(c.latitude AS FLOAT64)))
                * COS(RADIANS(CAST(c.longitude AS FLOAT64)) - RADIANS({lon_polo}))
                + SIN(RADIANS({lat_polo})) * SIN(RADIANS(CAST(c.latitude AS FLOAT64)))
              ), 2
            )"""
        dist_col = f"{dist_expr} AS distancia_km,"
        order_by = "distancia_km ASC"
        join_cep = """
            LEFT JOIN `project-a8f8452a-3033-4dd8-99a.raw.cep_coordenadas` c
                ON e.cep = c.cep"""
    else:
        dist_col = "NULL AS distancia_km,"
        order_by = "e.capital_social DESC"
        join_cep = ""

    df = _run(f"""
        SELECT
            e.nome_empresa,
            e.razao_social,
            e.cnae_classe,
            e.cnae_fiscal_principal,
            e.cep,
            CONCAT(e.ddd, ' ', e.telefone) AS telefone,
            e.email,
            e.capital_social,
            e.data_inicio_atividade,
            e.natureza_juridica,
            {dist_col}
            cn.descricao AS descricao_cnae
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empresas` e
        LEFT JOIN `basedosdados.br_bd_diretorios_brasil.cnae_2` cn
            ON LPAD(e.cnae_classe, 5, '0') = cn.classe
        {join_cep}
        WHERE e.id_municipio = @municipio
          AND e.cnae_classe IN ({cnae_in})
        ORDER BY {order_by}
        LIMIT 2000
    """, {"municipio": id_municipio})

    return {
        "rows": df.to_dict(orient="records"),
        "total": len(df),
        "com_distancia": lat_polo is not None,
    }


# ─────────────────────────────────────────
# BLOCO 5 — Formandos por IES e área
# ─────────────────────────────────────────

def get_formandos(id_municipio: str, ano: int | None = None) -> dict:
    ano_filter = f"AND ano = {ano}" if ano else "AND ano = (SELECT MAX(ano) FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_mercado_superior` WHERE id_municipio = @municipio)"

    df = _run(f"""
        SELECT
            nome_ies,
            rede,
            modalidade_ensino,
            nome_area_geral,
            nome_area_especifica,
            nome_area_detalhada,
            ano,
            SUM(total_vagas)        AS total_vagas,
            SUM(total_inscritos)    AS total_inscritos,
            SUM(total_ingressantes) AS total_ingressantes,
            SUM(total_matriculas)   AS total_matriculas,
            SUM(total_concluintes)  AS total_concluintes
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_mercado_superior`
        WHERE id_municipio = @municipio
          {ano_filter}
        GROUP BY 1,2,3,4,5,6,7
        ORDER BY total_concluintes DESC
    """, {"municipio": id_municipio})

    # Anos disponíveis para o seletor
    anos_df = _run("""
        SELECT DISTINCT ano FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_mercado_superior`
        WHERE id_municipio = @municipio ORDER BY ano DESC
    """, {"municipio": id_municipio})

    return {
        "rows": df.to_dict(orient="records"),
        "total_concluintes": int(df["total_concluintes"].sum()) if len(df) else 0,
        "anos_disponiveis": anos_df["ano"].tolist() if len(anos_df) else [],
    }


# ─────────────────────────────────────────
# BLOCO 6 — Score de atratividade
# ─────────────────────────────────────────

def get_score(id_municipio: str, sigla_uf: str, renda_minima: float) -> dict:
    # 1. Volume elegível: vinculos elegíveis / pop 25+ com superior (normalizado)
    vol_df = _run("""
        SELECT
            SUM(CASE WHEN e.salario_medio_reais >= @renda_min THEN e.total_vinculos ELSE 0 END) AS elegiveis,
            d.populacao_total,
            d.taxa_superior_25_mais
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos` e
        JOIN `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio` d
            ON e.id_municipio = d.id_municipio
        WHERE e.id_municipio = @municipio AND e.ano = 2022
        GROUP BY d.populacao_total, d.taxa_superior_25_mais
    """, {"municipio": id_municipio, "renda_min": renda_minima})

    # 2. Crescimento: variação de vínculos elegíveis 2020→2022
    trend_df = _run("""
        SELECT ano, SUM(CASE WHEN salario_medio_reais >= @renda_min THEN total_vinculos ELSE 0 END) AS elegiveis
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empregos`
        WHERE id_municipio = @municipio AND ano IN (2020, 2022)
        GROUP BY ano ORDER BY ano
    """, {"municipio": id_municipio, "renda_min": renda_minima})

    # 3. Capacidade corporativa: mediana capital social das empresas elegíveis
    cap_df = _run("""
        SELECT APPROX_QUANTILES(e.capital_social, 2)[OFFSET(1)] AS mediana_cap
        FROM `project-a8f8452a-3033-4dd8-99a.raw_facts.fct_empresas` e
        WHERE e.id_municipio = @municipio AND e.capital_social > 0
    """, {"municipio": id_municipio})

    # 4. Renda per capita relativa à UF
    renda_df = _run("""
        SELECT
            d.renda_per_capita AS cidade_renda,
            uf.uf_renda
        FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio` d
        CROSS JOIN (
            SELECT AVG(renda_per_capita) AS uf_renda
            FROM `project-a8f8452a-3033-4dd8-99a.raw_dimensions.dim_municipio`
            WHERE sigla_uf = @uf
        ) uf
        WHERE d.id_municipio = @municipio
    """, {"municipio": id_municipio, "uf": sigla_uf})

    def clamp(v, mn=0.0, mx=2.5): return round(max(mn, min(mx, v)), 2)

    # Dimensão 1: volume elegível por pop. formada (escala: 5% = 2.5 pts)
    d1 = 0.0
    if len(vol_df) and vol_df.iloc[0]["taxa_superior_25_mais"]:
        row = vol_df.iloc[0]
        pop_formada = (row["populacao_total"] or 0) * (row["taxa_superior_25_mais"] or 0) / 100
        ratio = (row["elegiveis"] or 0) / max(pop_formada, 1)
        d1 = clamp(ratio * 50)  # 5% penetração = pontuação máxima

    # Dimensão 2: crescimento (escala: 20% crescimento = 2.5 pts)
    d2 = 0.0
    if len(trend_df) == 2:
        e2020 = trend_df[trend_df["ano"] == 2020]["elegiveis"].values[0] or 1
        e2022 = trend_df[trend_df["ano"] == 2022]["elegiveis"].values[0] or 0
        growth = (e2022 - e2020) / e2020
        d2 = clamp(growth * 12.5)

    # Dimensão 3: capacidade corporativa (escala: mediana R$10M = 2.5 pts)
    d3 = 0.0
    if len(cap_df) and cap_df.iloc[0]["mediana_cap"]:
        mediana = cap_df.iloc[0]["mediana_cap"]
        d3 = clamp((mediana / 10_000_000) * 2.5)

    # Dimensão 4: renda relativa à UF (escala: 2x a média = 2.5 pts)
    d4 = 0.0
    if len(renda_df) and renda_df.iloc[0]["uf_renda"]:
        row = renda_df.iloc[0]
        ratio = (row["cidade_renda"] or 0) / max(row["uf_renda"], 1)
        d4 = clamp((ratio - 0.5) * 2.5)  # ≥0.5x da UF começa a pontuar

    score = round(d1 + d2 + d3 + d4, 1)

    return {
        "score": score,
        "score_max": 10.0,
        "dimensoes": {
            "volume_elegivel":       {"valor": d1, "max": 2.5, "label": "Volume elegível"},
            "crescimento":           {"valor": d2, "max": 2.5, "label": "Crescimento 2020→2022"},
            "capacidade_corporativa":{"valor": d3, "max": 2.5, "label": "Capacidade corporativa"},
            "renda_relativa":        {"valor": d4, "max": 2.5, "label": "Renda per capita relativa"},
        },
    }


# ─────────────────────────────────────────
# BLOCO 7 — Contexto para o LLM
# ─────────────────────────────────────────

def get_llm_context(
    id_municipio: str,
    sigla_uf: str,
    produto: str,
    mensalidade: float,
    percentual_renda: float,
    perfil: dict,
    vinculos: dict,
    estabelecimentos: dict,
    formandos: dict,
    score: dict,
) -> str:
    renda_min = mensalidade / (percentual_renda / 100)

    cidade = perfil.get("nome_municipio", id_municipio)

    # Top 10 cargos elegíveis
    top_cargos = sorted(
        [r for r in vinculos["rows"] if r.get("elegivel")],
        key=lambda r: r.get("total_vinculos", 0), reverse=True
    )[:10]

    # Top 10 setores por estabelecimentos
    top_setores = sorted(
        estabelecimentos["rows"],
        key=lambda r: r.get("vinculos_elegiveis", 0), reverse=True
    )[:10]

    # Top areas de formação
    top_areas = {}
    for r in formandos["rows"]:
        area = r.get("nome_area_especifica", "Outros")
        top_areas[area] = top_areas.get(area, 0) + (r.get("total_concluintes") or 0)
    top_areas = sorted(top_areas.items(), key=lambda x: x[1], reverse=True)[:10]

    perfil_rows = "\n".join(
        f"  - {r['metrica']}: {r['cidade']} (UF: {r['uf_media']}, delta: {r['delta_pct']}%)"
        for r in perfil.get("rows", [])
    )

    cargos_txt = "\n".join(
        f"  - {r.get('descricao_cargo', '?')} | {r.get('descricao_subsetor', '?')} | "
        f"Vínculos: {r.get('total_vinculos', 0):,} | Salário médio: R$ {r.get('salario_medio_reais', 0):,.0f}"
        for r in top_cargos
    )

    setores_txt = "\n".join(
        f"  - {r.get('descricao_cnae') or r.get('descricao_subsetor', '?')} | "
        f"Estab: {r.get('total_estabelecimentos', 0):,} | Vínculos elegíveis: {r.get('vinculos_elegiveis', 0):,} | "
        f"% elegível: {r.get('pct_elegivel', 0)}%"
        for r in top_setores
    )

    areas_txt = "\n".join(f"  - {a}: {n:,} concluintes" for a, n in top_areas)

    return f"""
Você é um analista de inteligência de mercado da FGV (Fundação Getulio Vargas).
Analise os dados abaixo e produza um relatório executivo em português sobre o potencial de {produto} em {cidade}/{sigla_uf}.

=== CONTEXTO ===
Produto: {produto}
Mensalidade: R$ {mensalidade:,.2f}/mês
Percentual de renda dedicado: {percentual_renda}%
Renda mínima necessária: R$ {renda_min:,.2f}/mês
Score de atratividade: {score['score']}/10

=== PERFIL SOCIOECONÔMICO ===
{perfil_rows}

=== MERCADO DE TRABALHO (top cargos elegíveis) ===
Total de vínculos elegíveis: {vinculos['total_elegiveis']:,}
Total de vínculos na cidade: {vinculos['total_vinculos']:,}
{cargos_txt}

=== DENSIDADE EMPRESARIAL (top setores por vínculos elegíveis) ===
{setores_txt}

=== PIPELINE DE AUDIÊNCIA (áreas de formação — concluintes acumulados) ===
{areas_txt}

=== INSTRUÇÕES ===
Escreva 4 parágrafos executivos:
1. Dimensionamento de mercado: tamanho e perfil do público-alvo em {cidade}
2. Setores prioritários: quais setores concentram o maior potencial e por quê — sugira portfólio de {produto} aderente à economia local (sem inventar dados, só interprete o que está acima)
3. Estratégia de prospecção: canal corporativo vs. individual, quais tipos de empresa priorizar, como abordar universidades parceiras para recém-formados
4. Riscos e oportunidades: o que pode limitar a expansão e o que joga a favor

Seja direto e específico. Use os dados. Não invente informações além do que foi fornecido.
"""
