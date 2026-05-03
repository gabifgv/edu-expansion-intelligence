"""
Camada de queries DuckDB para o dashboard FGV consolidado.
Lê de data/sp_mvp.duckdb (filtrado para SP) e retorna payloads prontos para o frontend.
"""
import duckdb
import json
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "sp_mvp.duckdb"
PROMPT_PATH = Path(__file__).parent.parent / "data" / "prompt_b7.json"

# ── Deflatores IPCA (BCB série 433) — fallback hardcoded se API falhar ────────
_IPCA_2010 = None
_IPCA_2022 = None

def _get_ipca(data_inicial: str, fallback: float):
    """Calcula fator de inflação acumulado desde data_inicial até hoje (BCB série 433)."""
    try:
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={data_inicial}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            dados = json.loads(r.read())
        fator = 1.0
        for d in dados:
            fator *= (1 + float(d["valor"]) / 100)
        return fator
    except Exception:
        return fallback

def get_ipca_2010():
    global _IPCA_2010
    if _IPCA_2010 is None:
        _IPCA_2010 = _get_ipca("01/08/2010", 2.4254)
    return _IPCA_2010

def get_ipca_2022():
    global _IPCA_2022
    if _IPCA_2022 is None:
        _IPCA_2022 = _get_ipca("01/12/2022", 1.1727)
    return _IPCA_2022

# ── Conexão (read-only para suportar threads) ─────────────────────────────────
def get_con():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("SET enable_progress_bar=false")
    return con

# ── Filtros: lista de UFs e municípios ────────────────────────────────────────
def list_ufs():
    con = get_con()
    df = con.execute("SELECT DISTINCT sigla_uf FROM dim_municipio ORDER BY sigla_uf").df()
    con.close()
    return df["sigla_uf"].tolist()

def list_municipios(sigla_uf: str):
    con = get_con()
    df = con.execute(f"""
        SELECT id_municipio, nome_municipio, populacao_total
        FROM dim_municipio
        WHERE sigla_uf = '{sigla_uf}'
        ORDER BY nome_municipio
    """).df()
    con.close()
    return df.to_dict(orient="records")

# ── BLOCO 1: Perfil Socioeconômico ────────────────────────────────────────────
def get_perfil(con, id_municipio: str, sigla_uf: str, renda_min: float, ano_emp: int):
    cidade = con.execute(f"""
        SELECT nome_municipio, populacao_total, populacao_18_24, idhm, idhm_educacao,
               renda_per_capita, indice_gini, taxa_superior_25_mais, prop_pobreza
        FROM dim_municipio WHERE id_municipio = '{id_municipio}'
    """).df().iloc[0].to_dict()

    uf = con.execute(f"""
        SELECT
            SUM(idhm * populacao_total) / NULLIF(SUM(populacao_total),0) AS idhm,
            SUM(renda_per_capita * populacao_total) / NULLIF(SUM(populacao_total),0) AS renda_per_capita,
            SUM(indice_gini * populacao_total) / NULLIF(SUM(populacao_total),0) AS indice_gini,
            SUM(populacao_total) AS populacao_total,
            SUM(taxa_superior_25_mais * populacao_total) / NULLIF(SUM(populacao_total),0) AS taxa_superior_25_mais,
            SUM(prop_pobreza * populacao_total) / NULLIF(SUM(populacao_total),0) AS prop_pobreza
        FROM dim_municipio WHERE sigla_uf = '{sigla_uf}'
    """).df().iloc[0].to_dict()

    # Elegíveis (cidade vs uf) usando o ano mais recente de empregos
    eleg_c = con.execute(f"""
        SELECT SUM(total_vinculos) v,
               SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) e,
               SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) AS sal_medio
        FROM fct_empregos WHERE id_municipio = '{id_municipio}' AND ano = {ano_emp}
    """).fetchone()
    eleg_u = con.execute(f"""
        SELECT SUM(total_vinculos) v,
               SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) e,
               SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) AS sal_medio
        FROM fct_empregos WHERE sigla_uf = '{sigla_uf}' AND ano = {ano_emp}
    """).fetchone()

    pct_c = (eleg_c[1] / eleg_c[0] * 100) if eleg_c[0] else 0.0
    pct_u = (eleg_u[1] / eleg_u[0] * 100) if eleg_u[0] else 0.0

    # Aplica IPCA: Atlas 2010 → presente / RAIS 2022 → presente
    ipca_2010 = get_ipca_2010()
    ipca_2022 = get_ipca_2022()
    renda_pc_c = (cidade["renda_per_capita"] or 0) * ipca_2010
    renda_pc_u = (uf["renda_per_capita"] or 0) * ipca_2010
    sal_rais_c = (eleg_c[2] or 0) * ipca_2022
    sal_rais_u = (eleg_u[2] or 0) * ipca_2022

    # Métricas: type="pp" usa pontos percentuais (delta absoluto), "pct" usa variação percentual
    # Gini: para produto premium FGV, alta concentração de renda no topo é positiva → direction "higher"
    metricas = [
        ("IDHM geral",                  cidade["idhm"],                  uf["idhm"],                  "higher", "pct"),
        ("Renda per capita (R$/mês)",   renda_pc_c,                      renda_pc_u,                  "higher", "pct"),
        ("Renda média RAIS (R$/mês)",   sal_rais_c,                      sal_rais_u,                  "higher", "pct"),
        ("Índice de Gini",              cidade["indice_gini"],           uf["indice_gini"],           "higher", "pct"),
        ("Pop. 25+ com superior",       cidade["taxa_superior_25_mais"], uf["taxa_superior_25_mais"], "higher", "pp"),
        ("Proporção em pobreza",        cidade["prop_pobreza"],          uf["prop_pobreza"],          "lower",  "pp"),
        ("Elegíveis / vínculos",        pct_c,                           pct_u,                       "higher", "pp"),
    ]
    rows = []
    for label, c_val, u_val, direction, dtype in metricas:
        delta = None
        delta_type = dtype
        status = "neutral"
        if u_val is not None and c_val is not None:
            if dtype == "pp":
                # diferença absoluta em pontos percentuais
                delta = float(c_val) - float(u_val)
            elif dtype == "pct" and u_val != 0:
                # variação percentual relativa
                delta = (float(c_val) - float(u_val)) / abs(float(u_val)) * 100
            if delta is not None:
                if direction == "higher":
                    status = "above" if delta > 0 else "below"
                elif direction == "lower":
                    status = "above" if delta < 0 else "below"
        rows.append({
            "metrica": label,
            "cidade": float(c_val) if c_val is not None else None,
            "uf": float(u_val) if u_val is not None else None,
            "delta": float(delta) if delta is not None else None,
            "delta_type": delta_type,
            "status": status,
        })

    return {
        "cidade_nome": cidade["nome_municipio"],
        "sigla_uf": sigla_uf,
        "populacao": int(cidade["populacao_total"] or 0),
        "ipca_2010": round(ipca_2010, 4),
        "ipca_2022": round(ipca_2022, 4),
        "rows": rows,
    }

# ── BLOCO 2+3: Mercado de Trabalho + Tecido Empresarial ──────────────────────
def get_mercado_trabalho(con, id_municipio: str, renda_min: float, ano_emp: int):
    # Tabela 1: por setor (com estabelecimentos)
    df_setor = con.execute(f"""
        WITH emp AS (
            SELECT descricao_subsetor,
                   SUM(total_vinculos) AS vinculos,
                   SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) AS sal_medio,
                   SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) AS eleg,
                   SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos*salario_medio_reais ELSE 0 END)
                       / NULLIF(SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END),0) AS sal_eleg
            FROM fct_empregos
            WHERE id_municipio = '{id_municipio}' AND ano = {ano_emp} AND descricao_subsetor IS NOT NULL
            GROUP BY 1
        ),
        est AS (
            SELECT descricao_subsetor, SUM(total_estabelecimentos) AS estabs
            FROM fct_estabelecimentos
            WHERE id_municipio = '{id_municipio}' AND ano = {ano_emp}
            GROUP BY 1
        )
        SELECT
            e.descricao_subsetor AS setor,
            COALESCE(es.estabs, 0) AS estabs,
            ROUND(e.vinculos / NULLIF(es.estabs,0), 1) AS func_por_emp,
            CAST(e.vinculos AS BIGINT) AS vinculos,
            ROUND(e.sal_medio, 0) AS sal_medio,
            CAST(e.eleg AS BIGINT) AS eleg,
            ROUND(100.0 * e.eleg / NULLIF(e.vinculos,0), 1) AS pct_eleg,
            CASE WHEN e.eleg >= 5 THEN ROUND(e.sal_eleg, 0) ELSE NULL END AS sal_eleg
        FROM emp e
        LEFT JOIN est es ON es.descricao_subsetor = e.descricao_subsetor
        ORDER BY e.eleg DESC NULLS LAST
    """).df()

    # Tabela 2: por cargo (sem agrupar por setor — vamos usar setor como filtro client-side)
    df_cargo_raw = con.execute(f"""
        SELECT
            descricao_subsetor AS setor,
            descricao_cargo    AS cargo,
            SUM(total_vinculos) AS vinculos,
            SUM(total_vinculos * salario_medio_reais) AS soma_sal_total,
            SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos ELSE 0 END) AS eleg,
            SUM(CASE WHEN salario_medio_reais >= {renda_min} THEN total_vinculos*salario_medio_reais ELSE 0 END) AS soma_sal_eleg
        FROM fct_empregos
        WHERE id_municipio = '{id_municipio}' AND ano = {ano_emp}
          AND descricao_cargo IS NOT NULL AND descricao_subsetor IS NOT NULL
        GROUP BY 1, 2
    """).df()

    # Agregado por cargo (sem setor) para a tabela exibida
    df_cargo = df_cargo_raw.groupby("cargo", as_index=False).agg(
        vinculos=("vinculos", "sum"),
        soma_sal_total=("soma_sal_total", "sum"),
        eleg=("eleg", "sum"),
        soma_sal_eleg=("soma_sal_eleg", "sum"),
    )
    df_cargo["sal_medio"] = (df_cargo["soma_sal_total"] / df_cargo["vinculos"]).round(0)
    df_cargo["pct_eleg"]  = (df_cargo["eleg"] / df_cargo["vinculos"] * 100).round(1)
    df_cargo["sal_eleg"]  = (df_cargo["soma_sal_eleg"] / df_cargo["eleg"].replace(0, float("nan"))).round(0)
    df_cargo.loc[df_cargo["eleg"] < 5, "sal_eleg"] = None
    df_cargo = df_cargo[df_cargo["eleg"] > 0].sort_values("eleg", ascending=False)
    df_cargo["sal_eleg"] = df_cargo["sal_eleg"].where(df_cargo["sal_eleg"].notna(), None)

    # Tabela cargo × setor (para filtro client-side)
    cargo_setor = df_cargo_raw.copy()
    cargo_setor["pct_eleg"] = (cargo_setor["eleg"] / cargo_setor["vinculos"] * 100).round(1)
    cargo_setor["sal_medio"] = (cargo_setor["soma_sal_total"] / cargo_setor["vinculos"]).round(0)
    cargo_setor["sal_eleg"] = (cargo_setor["soma_sal_eleg"] / cargo_setor["eleg"].replace(0, float("nan"))).round(0)
    cargo_setor.loc[cargo_setor["eleg"] < 5, "sal_eleg"] = None
    cargo_setor = cargo_setor[cargo_setor["eleg"] > 0]

    setores_unicos = sorted(df_cargo_raw["setor"].dropna().unique().tolist())

    total_vinculos = int(df_setor["vinculos"].sum()) if len(df_setor) else 0
    total_eleg     = int(df_setor["eleg"].sum()) if len(df_setor) else 0
    sal_eleg_pond  = float((df_setor["sal_eleg"] * df_setor["eleg"]).sum() / df_setor["eleg"].sum()) if total_eleg else 0

    # Aplica IPCA aos salários
    ipca = get_ipca_2022()
    if "sal_medio" in df_setor.columns:
        df_setor["sal_medio"] = (df_setor["sal_medio"] * ipca).round(0)
        df_setor["sal_eleg"] = (df_setor["sal_eleg"] * ipca).round(0)
    if "sal_medio" in df_cargo.columns:
        df_cargo["sal_medio"] = (df_cargo["sal_medio"] * ipca).round(0)
        df_cargo["sal_eleg"] = (df_cargo["sal_eleg"] * ipca).round(0)
    if "sal_medio" in cargo_setor.columns:
        cargo_setor["sal_medio"] = (cargo_setor["sal_medio"] * ipca).round(0)
        cargo_setor["sal_eleg"] = (cargo_setor["sal_eleg"] * ipca).round(0)
    sal_eleg_pond = sal_eleg_pond * ipca

    # Série temporal de estabelecimentos por ano (total no município) — exclui 2022 (broken na fonte)
    df_estab_serie = con.execute(f"""
        SELECT ano, SUM(total_estabelecimentos) AS estabs
        FROM fct_estabelecimentos
        WHERE id_municipio = '{id_municipio}' AND ano != 2022
        GROUP BY ano ORDER BY ano
    """).df()

    # Série temporal de estabelecimentos por ano × setor (para filtragem client-side)
    df_estab_serie_setor = con.execute(f"""
        SELECT ano, descricao_subsetor AS setor, SUM(total_estabelecimentos) AS estabs
        FROM fct_estabelecimentos
        WHERE id_municipio = '{id_municipio}' AND ano != 2022
          AND descricao_subsetor IS NOT NULL
        GROUP BY 1, 2 ORDER BY 1, 2
    """).df()

    return {
        "ano": ano_emp,
        "renda_min": renda_min,
        "kpis": {
            "total_vinculos": total_vinculos,
            "elegiveis": total_eleg,
            "pct_elegiveis": round(total_eleg / total_vinculos * 100, 1) if total_vinculos else 0,
            "sal_eleg_medio": round(sal_eleg_pond, 0),
        },
        "por_setor": _df_to_records(df_setor),
        "por_cargo": _df_to_records(df_cargo[["cargo", "vinculos", "sal_medio", "eleg", "pct_eleg", "sal_eleg"]]),
        "cargo_setor": _df_to_records(cargo_setor[["setor", "cargo", "vinculos", "sal_medio", "eleg", "pct_eleg", "sal_eleg"]]),
        "setores_unicos": setores_unicos,
        "estab_serie": _df_to_records(df_estab_serie),
        "estab_serie_setor": _df_to_records(df_estab_serie_setor),
    }

# ── BLOCO 4: Empresas-Alvo ────────────────────────────────────────────────────
def get_empresas(con, id_municipio: str, capital_min: float = 500_000,
                 lat_polo: float = None, lon_polo: float = None, limit: int = 200):
    # Distância haversine direto no SQL se houver polo (fallback rápido sem OSRM no dashboard)
    if lat_polo is not None and lon_polo is not None:
        dist_expr = f"""ROUND(2 * 6371 * ASIN(SQRT(
            POWER(SIN(RADIANS(c.latitude  - {lat_polo}) / 2), 2) +
            COS(RADIANS({lat_polo})) * COS(RADIANS(c.latitude)) *
            POWER(SIN(RADIANS(c.longitude - {lon_polo}) / 2), 2)
        )), 2)"""
        order = "distancia_km"
        join_coords = "JOIN dim_cep_coords c ON c.cep = e.cep"
    else:
        dist_expr = "NULL"
        order = "e.capital_social DESC"
        join_coords = ""

    df = con.execute(f"""
        WITH sl AS (
            SELECT cnae_classe, descricao_subsetor, SUM(total_vinculos) AS v
            FROM fct_empregos WHERE cnae_classe IS NOT NULL GROUP BY 1, 2
        ),
        slookup AS (
            SELECT DISTINCT ON (cnae_classe) cnae_classe, descricao_subsetor
            FROM sl ORDER BY cnae_classe, v DESC
        )
        SELECT
            e.nome_empresa,
            COALESCE(sl.descricao_subsetor, 'Não Classificado') AS setor,
            e.cep,
            COALESCE('(' || e.ddd || ') ' || e.telefone, '-') AS telefone,
            COALESCE(e.email, '-') AS email,
            e.capital_social,
            {dist_expr} AS distancia_km
        FROM fct_empresas e
        {join_coords}
        LEFT JOIN slookup sl ON sl.cnae_classe = e.cnae_classe
        WHERE e.id_municipio = '{id_municipio}'
          AND e.porte = '5'
          AND e.capital_social >= {capital_min}
        ORDER BY {order}
        LIMIT {limit}
    """).df()

    total = con.execute(f"""
        SELECT COUNT(*) FROM fct_empresas e
        WHERE e.id_municipio = '{id_municipio}'
          AND e.porte = '5' AND e.capital_social >= {capital_min}
    """).fetchone()[0]

    setores_unicos = sorted([s for s in df["setor"].unique().tolist() if s and s != "Não Classificado"])

    return {
        "total": int(total),
        "exibidos": len(df),
        "rows": _df_to_records(df),
        "setores_unicos": setores_unicos,
        "com_distancia": lat_polo is not None,
    }

# ── BLOCO 5: Pipeline Universitário ───────────────────────────────────────────
def get_pipeline(con, id_municipio: str):
    # Carrega TODOS os anos para permitir filtros e tratamento de reclassificação client-side
    df = con.execute(f"""
        SELECT
            ano,
            COALESCE(nome_area_geral, 'Não classificado') AS area,
            COALESCE(nome_area_detalhada, '-') AS curso,
            COALESCE(nome_ies, '-') AS ies,
            COALESCE(rede, '-') AS rede,
            COALESCE(modalidade_ensino, '-') AS modalidade,
            SUM(total_concluintes) AS conc
        FROM fct_mercado_superior
        WHERE id_municipio = '{id_municipio}'
        GROUP BY 1, 2, 3, 4, 5, 6
    """).df()

    if len(df) == 0:
        return {
            "kpis": {"c2024": 0, "c2023": 0, "c2020": 0, "ies24": 0, "delta_23": 0, "delta_20": 0},
            "rows": [],
            "areas_unicas": [],
            "ies_unicas": [],
            "anos": [],
        }

    anos_disponiveis = sorted(df["ano"].unique().tolist())
    ano_max = max(anos_disponiveis)

    # KPIs
    c24 = int(df[df["ano"] == ano_max]["conc"].sum())
    c23 = int(df[df["ano"] == ano_max - 1]["conc"].sum()) if (ano_max - 1) in anos_disponiveis else 0
    c20 = int(df[df["ano"] == 2020]["conc"].sum()) if 2020 in anos_disponiveis else 0
    ies24 = int(df[df["ano"] == ano_max]["ies"].nunique())

    delta_23 = ((c24 - c23) / c23 * 100) if c23 else 0
    delta_20 = ((c24 - c20) / c20 * 100) if c20 else 0

    # ── Cursos em Alta com tratamento de reclassificação INEP ────────────────
    # Para cada (área, curso): se o curso sumiu em ano_max mas existia em 2020,
    # somar como baseline da área. Isso compensa consolidações INEP (ex: TIC 2024).
    agg_curso = df.groupby(["area", "curso"], as_index=False).agg(
        c24=("conc", lambda x: x[df.loc[x.index, "ano"] == ano_max].sum()),
        c20=("conc", lambda x: x[df.loc[x.index, "ano"] == 2020].sum()),
    )
    # Baseline por área: cursos que sumiram em ano_max
    area_baseline = (
        agg_curso[(agg_curso["c24"] == 0) & (agg_curso["c20"] > 0)]
        .groupby("area")["c20"].sum()
        .to_dict()
    )

    cursos_alta_list = []
    for _, row in agg_curso.iterrows():
        if row["c24"] < 100:  # mínimo de volume
            continue
        if row["c20"] > 0 and row["c24"] > row["c20"]:
            # crescimento direto
            cresc = (row["c24"] - row["c20"]) / row["c20"] * 100
            nota = ""
        elif row["c20"] == 0 and row["area"] in area_baseline and area_baseline[row["area"]] > 0:
            # curso novo — usa baseline da área (reclassificação)
            base = area_baseline[row["area"]]
            cresc = (row["c24"] - base) / base * 100
            nota = "reclassif."
        else:
            continue
        if cresc <= 0:
            continue
        cursos_alta_list.append({
            "area": row["area"],
            "curso": row["curso"],
            "c24": int(row["c24"]),
            "c20": int(row["c20"]) if not nota else int(area_baseline.get(row["area"], 0)),
            "cresc": round(float(cresc), 1),
            "nota": nota,
        })
    # Ordena por (volume × crescimento) para priorizar cursos em alta com massa
    cursos_alta_list.sort(key=lambda x: (x["c24"] / 1000) * (x["cresc"] / 100), reverse=True)
    cursos_alta_list = cursos_alta_list[:10]

    # Top IES com volume e perfil
    ies_max = df[df["ano"] == ano_max].groupby(["ies", "rede"], as_index=False)["conc"].sum()
    ies_max = ies_max.sort_values("conc", ascending=False).head(10)

    # ── Áreas em alta: agrupa cursos por área ────────────────────────────────
    areas_alta = {}
    for c in cursos_alta_list:
        if c["area"] not in areas_alta:
            areas_alta[c["area"]] = {
                "area": c["area"],
                "total_c24": 0,
                "total_c20_baseline": 0,
                "cursos": [],
            }
        areas_alta[c["area"]]["total_c24"] += c["c24"]
        areas_alta[c["area"]]["total_c20_baseline"] += c.get("c20", 0)
        areas_alta[c["area"]]["cursos"].append({
            "curso": c["curso"],
            "c24": c["c24"],
            "cresc": c["cresc"],
            "nota": c["nota"],
        })

    areas_alta_list = []
    for area_data in areas_alta.values():
        # Crescimento da área = soma c24 vs soma baseline
        baseline = area_data["total_c20_baseline"]
        cresc_area = ((area_data["total_c24"] - baseline) / baseline * 100) if baseline else 0
        area_data["cresc"] = round(cresc_area, 1)
        # Ordena cursos dentro da área por volume
        area_data["cursos"].sort(key=lambda x: x["c24"], reverse=True)
        areas_alta_list.append(area_data)

    # Ordena áreas por (volume × crescimento)
    areas_alta_list.sort(key=lambda x: (x["total_c24"] / 1000) * (x["cresc"] / 100 if x["cresc"] > 0 else 0.01), reverse=True)

    return {
        "ano_max": ano_max,
        "kpis": {
            "c24": c24, "c23": c23, "c20": c20, "ies24": ies24,
            "delta_23": round(delta_23, 1),
            "delta_20": round(delta_20, 1),
        },
        "rows": _df_to_records(df),
        "areas_unicas": sorted(df["area"].unique().tolist()),
        "ies_unicas": sorted(df["ies"].unique().tolist()),
        "anos": anos_disponiveis,
        "cursos_alta": cursos_alta_list,
        "areas_alta": areas_alta_list,
        "top_ies": _df_to_records(ies_max),
    }

# ── BLOCO 6: Score de Atratividade (todas as 645 cidades SP pré-computadas) ──
def get_score_estado(con, sigla_uf: str, ano_emp: int):
    # D1
    df_d1 = con.execute(f"""
        SELECT e.id_municipio,
            SUM(e.total_vinculos * e.salario_medio_reais) / NULLIF(SUM(e.total_vinculos),0) AS avg_sal,
            SUM(CASE WHEN e.salario_medio_sm >= 3 THEN e.total_vinculos ELSE 0 END) * 1.0
                / NULLIF(SUM(e.total_vinculos),0) AS pct_3sm
        FROM fct_empregos e
        JOIN dim_municipio d ON d.id_municipio = e.id_municipio
        WHERE d.sigla_uf = '{sigla_uf}' AND e.ano = {ano_emp}
        GROUP BY 1
    """).df()

    # D2
    df_d2 = con.execute(f"""
        WITH v AS (SELECT id_municipio, SUM(total_vinculos) AS vinculos FROM fct_empregos WHERE ano = {ano_emp} GROUP BY 1),
        g AS (SELECT id_municipio, COUNT(DISTINCT cnpj) AS n_g FROM fct_empresas WHERE porte='5' AND capital_social >= 1000000 GROUP BY 1)
        SELECT d.id_municipio,
            COALESCE(v.vinculos,0) AS vinculos,
            COALESCE(g.n_g,0) * 1000.0 / NULLIF(COALESCE(v.vinculos,0),0) AS grandes_per_1k
        FROM dim_municipio d
        LEFT JOIN v ON v.id_municipio = d.id_municipio
        LEFT JOIN g ON g.id_municipio = d.id_municipio
        WHERE d.sigla_uf = '{sigla_uf}'
    """).df()

    # D3
    df_d3 = con.execute(f"""
        WITH conc AS (
            SELECT id_municipio,
                SUM(CASE WHEN nome_area_geral IN (
                    'Negócios, administração e direito',
                    'Tecnologias da informação e comunicação',
                    'Engenharia, produção e construção'
                ) THEN total_concluintes ELSE 0 END) AS c_alvo
            FROM fct_mercado_superior
            WHERE sigla_uf = '{sigla_uf}' AND ano = (SELECT MAX(ano) FROM fct_mercado_superior)
            GROUP BY 1
        )
        SELECT d.id_municipio,
            COALESCE(d.taxa_superior_25_mais, 0) AS taxa_sup,
            COALESCE(c.c_alvo,0) * 1000.0 / NULLIF(d.populacao_total,0) AS conc_per_1k
        FROM dim_municipio d
        LEFT JOIN conc c ON c.id_municipio = d.id_municipio
        WHERE d.sigla_uf = '{sigla_uf}'
    """).df()

    # D4
    df_d4 = con.execute(f"""
        WITH va AS (SELECT id_municipio, SUM(total_vinculos) v FROM fct_empregos WHERE ano = {ano_emp} GROUP BY 1),
        v0 AS (SELECT id_municipio, SUM(total_vinculos) v FROM fct_empregos WHERE ano = 2020 GROUP BY 1)
        SELECT d.id_municipio, COALESCE(d.idhm,0) AS idhm,
            CASE WHEN v0.v > 0 THEN (COALESCE(va.v,0) - v0.v)*1.0/v0.v ELSE NULL END AS cresc
        FROM dim_municipio d
        LEFT JOIN va ON va.id_municipio = d.id_municipio
        LEFT JOIN v0 ON v0.id_municipio = d.id_municipio
        WHERE d.sigla_uf = '{sigla_uf}'
    """).df()

    df_base = con.execute(f"""
        SELECT id_municipio, nome_municipio, populacao_total
        FROM dim_municipio WHERE sigla_uf = '{sigla_uf}'
    """).df()

    df = df_base.merge(df_d1, on="id_municipio", how="left") \
                .merge(df_d2, on="id_municipio", how="left") \
                .merge(df_d3, on="id_municipio", how="left") \
                .merge(df_d4, on="id_municipio", how="left")

    cols = ["avg_sal", "pct_3sm", "vinculos", "grandes_per_1k", "taxa_sup", "conc_per_1k", "idhm", "cresc"]
    df[cols] = df[cols].fillna(0)

    def norm(s):
        mn, mx = s.min(), s.max()
        return (s - mn) / (mx - mn + 1e-10)

    df["d1a"] = norm(df["avg_sal"])
    df["d1b"] = norm(df["pct_3sm"])
    df["d2a"] = norm(df["vinculos"])
    df["d2b"] = norm(df["grandes_per_1k"])
    df["d3a"] = norm(df["taxa_sup"])
    df["d3b"] = norm(df["conc_per_1k"])
    df["d4a"] = norm(df["idhm"])
    df["d4b"] = norm(df["cresc"])

    df["D1"] = ((df["d1a"] + df["d1b"]) / 2).round(4)
    df["D2"] = ((df["d2a"] + df["d2b"]) / 2).round(4)
    df["D3"] = ((df["d3a"] + df["d3b"]) / 2).round(4)
    df["D4"] = ((df["d4a"] + df["d4b"]) / 2).round(4)

    cidades = []
    for r in df.to_dict(orient="records"):
        cidades.append({
            "id": r["id_municipio"],
            "nm": r["nome_municipio"],
            "pop": int(r["populacao_total"]) if r["populacao_total"] else 0,
            "D1": float(r["D1"]),
            "D2": float(r["D2"]),
            "D3": float(r["D3"]),
            "D4": float(r["D4"]),
            "sal": round(float(r["avg_sal"]), 0),
            "vinc": int(r["vinculos"]),
            "tsup": round(float(r["taxa_sup"]), 1),
            "idhm": round(float(r["idhm"]), 3),
            "cresc": round(float(r["cresc"]) * 100, 1),
        })

    return {"cidades": cidades, "n": len(cidades)}

# ── BLOCO 7: chama Claude API com prompt completo ─────────────────────────────
def get_narrativa_llm(con, id_municipio: str, sigla_uf: str, produto: str,
                      mensalidade: float, pct_renda: float,
                      perfil_data: dict, mt_data: dict, empresas_data: dict,
                      pipeline_data: dict, score_data: dict,
                      api_key: str):
    import anthropic

    renda_min = mensalidade / (pct_renda / 100)
    ano_emp = mt_data.get("ano", 2024)

    # ── Perfil socioeconômico ──
    cidade_data = next((r for r in perfil_data["rows"] if "IDHM" in r["metrica"]), {})
    pop = perfil_data.get("populacao", 0)
    idhm = next((r["cidade"] for r in perfil_data["rows"] if r["metrica"] == "IDHM geral"), 0) or 0
    renda_pc = next((r["cidade"] for r in perfil_data["rows"] if "Renda per capita" in r["metrica"]), 0) or 0
    gini = next((r["cidade"] for r in perfil_data["rows"] if "Gini" in r["metrica"]), 0) or 0
    taxa_sup = next((r["cidade"] for r in perfil_data["rows"] if "superior" in r["metrica"]), 0) or 0
    pobreza = next((r["cidade"] for r in perfil_data["rows"] if "pobreza" in r["metrica"]), 0) or 0
    pct_eleg_c = next((r["cidade"] for r in perfil_data["rows"] if "Elegíveis" in r["metrica"]), 0) or 0

    nome_mun = perfil_data["cidade_nome"]

    DADOS_B1 = (
        f"Município: {nome_mun} | Pop. total: {int(pop):,}\n"
        f"IDHM: {idhm:.3f} | Renda per capita: R$ {renda_pc:,.0f} | Gini: {gini:.3f}\n"
        f"% pop 25+ com superior: {taxa_sup:.1f}% | Pobreza: {pobreza:.1f}%\n"
        f"% elegíveis (sal ≥ R${renda_min:,.0f}): {pct_eleg_c:.1f}%"
    )

    # ── Mercado de trabalho ──
    kpis_mt = mt_data["kpis"]
    top_setores = mt_data["por_setor"][:6]
    top_cargos = mt_data["por_cargo"][:8]
    set_str = "\n".join(
        f"  {r['setor']}: {int(r['vinculos']):,} vínc | {int(r['eleg']):,} elegíveis"
        for r in top_setores
    )
    cargo_str = "\n".join(
        f"  {r['cargo']}: {int(r['eleg']):,} eleg. | sal. médio eleg. R$ {int(r['sal_eleg']):,}"
        for r in top_cargos if r.get("sal_eleg")
    )
    DADOS_B23 = (
        f"Vínculos formais totais: {kpis_mt['total_vinculos']:,} | "
        f"Elegíveis: {kpis_mt['elegiveis']:,} ({kpis_mt['pct_elegiveis']}%)\n"
        f"Salário médio dos elegíveis: R$ {int(kpis_mt['sal_eleg_medio']):,}/mês\n\n"
        f"Top 6 setores por elegíveis:\n{set_str}\n\n"
        f"Top 8 cargos por elegíveis:\n{cargo_str}"
    )

    # ── Empresas-alvo ──
    top5 = empresas_data["rows"][:5]
    emp_str = "\n".join(
        f"  {r['nome_empresa']} | {r['setor']} | Capital: R$ {float(r['capital_social']):,.0f}"
        for r in top5
    )
    DADOS_B4 = f"Top 5 empresas (capital > R$1M):\n{emp_str}"

    # ── Pipeline universitário ──
    kpis_p = pipeline_data["kpis"]

    # Top IES e cursos em alta a partir das rows
    rows_pipe = pipeline_data["rows"]
    ano_max = pipeline_data["ano_max"]
    rows_max = [r for r in rows_pipe if r["ano"] == ano_max]
    ies_agg = {}
    for r in rows_max:
        ies_agg[r["ies"]] = ies_agg.get(r["ies"], {"conc": 0, "rede": r["rede"]})
        ies_agg[r["ies"]]["conc"] += r["conc"]
    top_ies = sorted(ies_agg.items(), key=lambda x: x[1]["conc"], reverse=True)[:5]
    ies_str = "\n".join(f"  {nm} ({d['rede']}): {int(d['conc']):,} conc." for nm, d in top_ies)

    # Cursos em alta — comparando ano_max vs 2020
    curso_agg = {}
    for r in rows_pipe:
        k = r["curso"]
        if k not in curso_agg:
            curso_agg[k] = {"c24": 0, "c20": 0}
        if r["ano"] == ano_max:
            curso_agg[k]["c24"] += r["conc"]
        elif r["ano"] == 2020:
            curso_agg[k]["c20"] += r["conc"]
    cursos_alta = []
    for k, v in curso_agg.items():
        if v["c24"] >= 200 and v["c20"] > 0 and v["c24"] > v["c20"]:
            cresc = (v["c24"] - v["c20"]) / v["c20"] * 100
            cursos_alta.append((k, v["c24"], cresc))
    cursos_alta.sort(key=lambda x: (x[1] / 1000) * (x[2] / 100), reverse=True)
    alta_str = "\n".join(f"  {k}: {int(c):,} conc. ({cr:+.0f}%)" for k, c, cr in cursos_alta[:6])

    DADOS_B5 = (
        f"Concluintes {ano_max}: {kpis_p['c24']:,} | IES: {kpis_p['ies24']} | "
        f"vs {ano_max-1}: {kpis_p['delta_23']:+.1f}% | vs 2020: {kpis_p['delta_20']:+.1f}%\n\n"
        f"Top 5 IES por volume:\n{ies_str}\n\n"
        f"Cursos em alta (volume + crescimento):\n{alta_str}"
    )

    # ── Score ──
    sel_id = id_municipio
    cidades = score_data["cidades"]
    sel = next((c for c in cidades if c["id"] == sel_id), None)
    if sel is None:
        sel = {"D1": 0, "D2": 0, "D3": 0, "D4": 0}

    # Aplica pesos default para o veredito (35/30/20/15)
    W = (0.35, 0.30, 0.20, 0.15)
    cidades_score = sorted(
        [(c["nm"], c["id"], (W[0]*c["D1"] + W[1]*c["D2"] + W[2]*c["D3"] + W[3]*c["D4"]) * 100) for c in cidades],
        key=lambda x: -x[2]
    )
    rank = next((i + 1 for i, (_, cid, _) in enumerate(cidades_score) if cid == sel_id), 0)
    score = cidades_score[rank - 1][2] if rank > 0 else 0

    D1 = round(sel["D1"] * 100)
    D2 = round(sel["D2"] * 100)
    D3 = round(sel["D3"] * 100)
    D4 = round(sel["D4"] * 100)

    # ── Carrega prompt template ──
    prompt_data = json.loads(PROMPT_PATH.read_text(encoding="utf-8"))
    SYSTEM = prompt_data["system"]
    template = prompt_data["user_template"]

    USER = (template
        .replace("{nome_municipio}", nome_mun)
        .replace("{sigla_uf}", sigla_uf)
        .replace("{produto}", produto)
        .replace("{mensalidade}", f"{int(mensalidade):,}")
        .replace("{renda_min}", f"{int(renda_min):,}")
        .replace("{pct_renda}", str(int(pct_renda)))
        .replace("{ano_emp}", str(ano_emp))
        .replace("{dados_b1}", DADOS_B1)
        .replace("{dados_b23}", DADOS_B23)
        .replace("{dados_b4}", DADOS_B4)
        .replace("{dados_b5}", DADOS_B5)
        .replace("{score}", f"{score:.1f}")
        .replace("{rank}", str(rank))
        .replace("{n_mun}", str(score_data["n"]))
        .replace("{D1}", str(D1))
        .replace("{D2}", str(D2))
        .replace("{D3}", str(D3))
        .replace("{D4}", str(D4))
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4500,
        system=SYSTEM,
        messages=[{"role": "user", "content": USER}],
    )
    return {
        "narrativa": response.content[0].text,
        "tokens": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        },
    }

# ── Helpers ──────────────────────────────────────────────────────────────────
def _df_to_records(df):
    """Converte DataFrame para lista de dicts substituindo NaN/Inf por None."""
    import pandas as pd
    import math
    records = df.where(pd.notna(df), None).to_dict(orient="records")
    return _clean_nan(records)

def _clean_nan(obj):
    """Recursivamente substitui NaN, Infinity e -Infinity por None.
    Necessário porque json.dumps não aceita esses valores."""
    import math
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_clean_nan(v) for v in obj)
    return obj
