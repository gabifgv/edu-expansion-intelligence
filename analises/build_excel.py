"""
Gera Excel completo (ano a ano) das 4 cidades de SP (Campinas/Jundiai/Piracicaba/Sorocaba)
+ estado de SP (ponderado por populacao). Aplica IPCA para deflacionar e calcular mercado
potencial a moeda constante.

Mensalidade = R$ 1.317, affordability = 9.5% -> renda minima 2024 = R$ 13.863,16
Para cada ano X, o limiar de elegibilidade equivalente eh renda_min_2024 / fator_IPCA(X->2024).

Saida: analises/out/dossie_4_pracas.xlsx
"""
import duckdb
import pandas as pd
from pathlib import Path

DB = r"C:\edu-expansion-intelligence\data\sp_mvp.duckdb"
OUT = Path(r"C:\edu-expansion-intelligence\analises\out\dossie_4_pracas.xlsx")

CIDADES = {
    "3509502": "Campinas",
    "3525904": "Jundiai",
    "3538709": "Piracicaba",
    "3552205": "Sorocaba",
}
IDS = list(CIDADES.keys())
IDS_SQL = "', '".join(IDS)

MENSALIDADE = 1317.0
PCT_RENDA = 9.5
RENDA_MIN_2024 = MENSALIDADE / (PCT_RENDA / 100.0)  # R$ 13.863,16

# IPCA acumulado anual (% no ano cheio) - fonte: IBGE/BCB serie 433
IPCA_ANUAL = {
    2020: 4.52,
    2021: 10.06,
    2022: 5.79,
    2023: 4.62,
    2024: 4.83,
}

# Anos validos por fonte (apos remocao dos buracos)
ANOS_EMPREGOS = [2020, 2021, 2022]              # fct_empregos cai 60% em 2023+ - quebra de fonte
ANOS_ESTAB    = [2020, 2021, 2023, 2024]        # fct_estabelecimentos 2022 esta 0.3% completo
ANOS_CURSOS   = [2020, 2021, 2022, 2023, 2024]  # fct_mercado_superior OK em todos
ANOS_EMPREGOS_SQL = ",".join(str(a) for a in ANOS_EMPREGOS)
ANOS_ESTAB_SQL    = ",".join(str(a) for a in ANOS_ESTAB)

# Fator para trazer reais de ANO_X para reais de 2024
# Ex: R$ 1 em 2020 vale R$ FATOR_2024[2020] em 2024
def fatores_para_2024():
    fat = {2024: 1.0}
    cur = 1.0
    for ano in [2023, 2022, 2021, 2020]:
        cur *= (1 + IPCA_ANUAL[ano + 1] / 100.0)
        fat[ano] = cur
    return fat

FATORES = fatores_para_2024()
# Limiar de renda em moeda NOMINAL do ano (mantendo poder de compra de R$ 13.863 de 2024)
RENDA_MIN_POR_ANO = {ano: RENDA_MIN_2024 / FATORES[ano] for ano in [2020, 2021, 2022, 2023, 2024]}


def conn():
    c = duckdb.connect(DB, read_only=True)
    c.execute("SET enable_progress_bar=false")
    return c


# ============================================================
# Aba 1 - Socioeconomico (4 cidades + SP ponderado por populacao)
# ============================================================
def aba_socioeconomico(c):
    ANO_RAIS = 2022  # ultimo ano limpo (RAIS oficial)

    cidades = c.execute(f"""
        SELECT id_municipio, nome_municipio,
               populacao_total,
               taxa_superior_25_mais,
               renda_per_capita,
               idhm, indice_gini, prop_pobreza
        FROM dim_municipio
        WHERE id_municipio IN ('{IDS_SQL}')
    """).df()

    sp = c.execute("""
        SELECT
            'SP_total' AS id_municipio,
            'Estado SP (ponderado)' AS nome_municipio,
            SUM(populacao_total) AS populacao_total,
            SUM(taxa_superior_25_mais * populacao_total)/NULLIF(SUM(populacao_total),0)      AS taxa_superior_25_mais,
            SUM(renda_per_capita * populacao_total)/NULLIF(SUM(populacao_total),0)           AS renda_per_capita,
            SUM(idhm * populacao_total)/NULLIF(SUM(populacao_total),0)                       AS idhm,
            SUM(indice_gini * populacao_total)/NULLIF(SUM(populacao_total),0)                AS indice_gini,
            SUM(prop_pobreza * populacao_total)/NULLIF(SUM(populacao_total),0)               AS prop_pobreza
        FROM dim_municipio
        WHERE sigla_uf = 'SP'
    """).df()

    full = pd.concat([cidades, sp], ignore_index=True)
    full["pop_25mais_com_superior_abs"] = (full["populacao_total"] * full["taxa_superior_25_mais"] / 100.0).round(0)

    # === RAIS por cidade (ano 2022) ===
    limiar_2022 = RENDA_MIN_POR_ANO[2022]
    rais_cid = c.execute(f"""
        SELECT id_municipio,
               SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) AS renda_media_rais,
               SUM(total_vinculos) AS vinc_total,
               SUM(CASE WHEN salario_medio_reais >= {limiar_2022} THEN total_vinculos ELSE 0 END) AS eleg,
               SUM(CASE WHEN salario_medio_reais >= {limiar_2022} THEN total_vinculos * salario_medio_reais ELSE 0 END)
                  / NULLIF(SUM(CASE WHEN salario_medio_reais >= {limiar_2022} THEN total_vinculos ELSE 0 END),0)
                  AS renda_media_elegiveis
        FROM fct_empregos
        WHERE ano = {ANO_RAIS}
          AND id_municipio IN ('{IDS_SQL}')
        GROUP BY id_municipio
    """).df()
    rais_cid["pct_elegiveis"] = (rais_cid["eleg"] / rais_cid["vinc_total"] * 100).round(2)

    # === RAIS Estado SP (ano 2022) ===
    rais_sp = c.execute(f"""
        SELECT 'SP_total' AS id_municipio,
               SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) AS renda_media_rais,
               SUM(total_vinculos) AS vinc_total,
               SUM(CASE WHEN salario_medio_reais >= {limiar_2022} THEN total_vinculos ELSE 0 END) AS eleg,
               SUM(CASE WHEN salario_medio_reais >= {limiar_2022} THEN total_vinculos * salario_medio_reais ELSE 0 END)
                  / NULLIF(SUM(CASE WHEN salario_medio_reais >= {limiar_2022} THEN total_vinculos ELSE 0 END),0)
                  AS renda_media_elegiveis
        FROM fct_empregos
        WHERE ano = {ANO_RAIS} AND sigla_uf = 'SP'
    """).df()
    rais_sp["pct_elegiveis"] = (rais_sp["eleg"] / rais_sp["vinc_total"] * 100).round(2)

    rais = pd.concat([rais_cid, rais_sp], ignore_index=True)
    rais_idx = rais.set_index("id_municipio")

    # Merge RAIS no socio
    full = full.set_index("id_municipio")
    full["renda_media_rais"] = rais_idx["renda_media_rais"]
    full["pct_elegiveis"] = rais_idx["pct_elegiveis"]
    full["renda_media_elegiveis"] = rais_idx["renda_media_elegiveis"]
    full = full.reset_index()

    # Aplica IPCA (2022 -> 2024) na renda RAIS para deixar comparavel com renda_per_capita (que ja eh contemporanea)
    fator = FATORES[ANO_RAIS]
    full["renda_media_rais_real_2024"] = (full["renda_media_rais"] * fator).round(0)
    full["renda_media_elegiveis_real_2024"] = (full["renda_media_elegiveis"] * fator).round(0)
    # elegiveis ABSOLUTOS (do rais)
    full["eleg_absoluto"] = rais_idx.reindex(full["id_municipio"])["eleg"].values

    # Montagem linha-por-metrica
    # comp_type: 'delta' (mostra % vs SP) | 'share' (mostra % do total SP)
    metricas = [
        ("taxa_superior_25_mais",              "Pop. 25+ com superior completo (%)",               2, "delta"),
        ("pop_25mais_com_superior_abs",        "Pop. 25+ com superior completo (absoluto)",        0, "share"),
        ("renda_per_capita",                   "Renda per capita (R$/mes)",                        2, "delta"),
        ("idhm",                               "IDHM geral",                                       3, "delta"),
        ("indice_gini",                        "Indice de Gini",                                   3, "delta"),
        ("prop_pobreza",                       "Proporcao em pobreza (%)",                         2, "delta"),
        ("renda_media_rais",                   f"Renda media RAIS {ANO_RAIS} (R$ nominal)",        0, "delta"),
        ("renda_media_rais_real_2024",         f"Renda media RAIS {ANO_RAIS} (R$ de 2024)",        0, "delta"),
        ("pct_elegiveis",                      f"% elegiveis (sal >= R$ {round(limiar_2022,0):.0f} em {ANO_RAIS})", 2, "delta"),
        ("eleg_absoluto",                      f"Qtd elegiveis {ANO_RAIS} (absoluto)",             0, "share"),
        ("renda_media_elegiveis",              f"Renda media dos elegiveis {ANO_RAIS} (R$ nominal)", 0, "delta"),
        ("renda_media_elegiveis_real_2024",    f"Renda media dos elegiveis {ANO_RAIS} (R$ de 2024)", 0, "delta"),
    ]
    rows = []
    ordem = ["3509502", "3525904", "3538709", "3552205", "SP_total"]
    nomes_col = {"3509502": "Campinas", "3525904": "Jundiai", "3538709": "Piracicaba",
                 "3552205": "Sorocaba", "SP_total": "Estado SP (ponderado)"}
    full_idx = full.set_index("id_municipio")
    for col, label, decs, comp in metricas:
        row = {"Metrica": label}
        for k in ordem:
            v = full_idx.loc[k, col] if k in full_idx.index else None
            row[nomes_col[k]] = round(v, decs) if v is not None and not pd.isna(v) else None
        sp_v = full_idx.loc["SP_total", col]
        if sp_v is not None and not pd.isna(sp_v) and sp_v != 0:
            for k in ordem[:-1]:
                cv = full_idx.loc[k, col]
                if cv is not None and not pd.isna(cv):
                    if comp == "share":
                        row[f"{nomes_col[k]} % do SP"] = round(cv / sp_v * 100, 2)
                    else:
                        row[f"{nomes_col[k]} vs SP %"] = round((cv - sp_v) / abs(sp_v) * 100, 1)
        rows.append(row)
    return pd.DataFrame(rows)


# ============================================================
# Aba 2 - KPIs mercado trabalho anual
# ============================================================
def aba_mt_kpis(c):
    rows = []
    for id_mun, nome in CIDADES.items():
        for ano in ANOS_EMPREGOS:
            limiar_nom = RENDA_MIN_POR_ANO[ano]
            r = c.execute(f"""
                SELECT
                    SUM(total_vinculos)                                                                AS vinc_total,
                    SUM(CASE WHEN salario_medio_reais >= {limiar_nom} THEN total_vinculos ELSE 0 END)  AS eleg_nominal,
                    SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0)          AS sal_medio_pond_nom,
                    SUM(CASE WHEN salario_medio_reais >= {limiar_nom} THEN total_vinculos * salario_medio_reais ELSE 0 END)
                        / NULLIF(SUM(CASE WHEN salario_medio_reais >= {limiar_nom} THEN total_vinculos ELSE 0 END),0)
                                                                                                       AS sal_eleg_pond_nom
                FROM fct_empregos
                WHERE id_municipio = '{id_mun}' AND ano = {ano}
            """).fetchone()
            vinc, eleg, sal_pond, sal_eleg = r
            f = FATORES[ano]
            rows.append({
                "cidade": nome,
                "ano": ano,
                "vinculos_total": int(vinc or 0),
                "elegiveis_eq_2024": int(eleg or 0),
                "pct_elegiveis": round((eleg / vinc * 100), 2) if vinc else None,
                "limiar_nominal_ano": round(limiar_nom, 0),
                "limiar_real_2024": RENDA_MIN_2024,
                "salario_medio_pond_nominal": round(sal_pond, 0) if sal_pond else None,
                "salario_medio_pond_real_2024": round(sal_pond * f, 0) if sal_pond else None,
                "salario_eleg_medio_nominal": round(sal_eleg, 0) if sal_eleg else None,
                "salario_eleg_medio_real_2024": round(sal_eleg * f, 0) if sal_eleg else None,
                "fator_ipca_para_2024": round(f, 4),
            })
    return pd.DataFrame(rows)


# ============================================================
# Aba 3 - Estabelecimentos anual
# ============================================================
def aba_estab(c):
    df = c.execute(f"""
        SELECT id_municipio, ano,
               SUM(total_estabelecimentos) AS estabelecimentos,
               SUM(total_vinculos_ativos)  AS vinculos_ativos
        FROM fct_estabelecimentos
        WHERE id_municipio IN ('{IDS_SQL}')
          AND ano IN ({ANOS_ESTAB_SQL})
        GROUP BY id_municipio, ano
        ORDER BY id_municipio, ano
    """).df()
    df["cidade"] = df["id_municipio"].map(CIDADES)
    return df[["cidade", "ano", "estabelecimentos", "vinculos_ativos"]]


# ============================================================
# Aba 5a - Setores: empregos (vinc + elegiveis + salario) - 2020-2022
# ============================================================
def aba_setores_empregos(c):
    df = c.execute(f"""
        SELECT id_municipio, ano, descricao_subsetor,
               SUM(total_vinculos) AS vinc_total,
               SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) AS sal_pond_nom
        FROM fct_empregos
        WHERE id_municipio IN ('{IDS_SQL}') AND ano IN ({ANOS_EMPREGOS_SQL})
        GROUP BY 1,2,3
    """).df()

    elig = c.execute(f"""
        SELECT id_municipio, ano, descricao_subsetor,
               SUM(CASE
                   WHEN ano=2020 AND salario_medio_reais >= {RENDA_MIN_POR_ANO[2020]} THEN total_vinculos
                   WHEN ano=2021 AND salario_medio_reais >= {RENDA_MIN_POR_ANO[2021]} THEN total_vinculos
                   WHEN ano=2022 AND salario_medio_reais >= {RENDA_MIN_POR_ANO[2022]} THEN total_vinculos
                   ELSE 0
               END) AS elegiveis_eq_2024
        FROM fct_empregos
        WHERE id_municipio IN ('{IDS_SQL}') AND ano IN ({ANOS_EMPREGOS_SQL})
        GROUP BY 1,2,3
    """).df()

    df = df.merge(elig, on=["id_municipio", "ano", "descricao_subsetor"], how="left")
    df["cidade"] = df["id_municipio"].map(CIDADES)
    df["fator_ipca_para_2024"] = df["ano"].map(FATORES)
    df["sal_pond_real_2024"] = (df["sal_pond_nom"] * df["fator_ipca_para_2024"]).round(0)
    df["pct_elegiveis"] = (df["elegiveis_eq_2024"] / df["vinc_total"].where(df["vinc_total"] > 0) * 100).round(2)
    df = df[[
        "cidade", "ano", "descricao_subsetor",
        "vinc_total", "elegiveis_eq_2024", "pct_elegiveis",
        "sal_pond_nom", "sal_pond_real_2024", "fator_ipca_para_2024",
    ]]
    return df.sort_values(["cidade", "ano", "vinc_total"], ascending=[True, True, False])


# ============================================================
# Aba 5b - Setores: estabelecimentos (2020, 2021, 2023, 2024)
# ============================================================
def aba_setores_estabs(c):
    df = c.execute(f"""
        SELECT id_municipio, ano, descricao_subsetor,
               SUM(total_estabelecimentos) AS estabs,
               SUM(total_vinculos_ativos)  AS vinc_ativos
        FROM fct_estabelecimentos
        WHERE id_municipio IN ('{IDS_SQL}') AND ano IN ({ANOS_ESTAB_SQL})
        GROUP BY 1,2,3
    """).df()
    df["cidade"] = df["id_municipio"].map(CIDADES)
    return df[[
        "cidade", "ano", "descricao_subsetor", "estabs", "vinc_ativos",
    ]].sort_values(["cidade", "ano", "estabs"], ascending=[True, True, False])


# ============================================================
# Aba 5 - Cargos (CBO) anual
# ============================================================
def aba_cargos(c):
    df = c.execute(f"""
        SELECT id_municipio, ano, cbo_2002, descricao_cargo,
               SUM(total_vinculos) AS vinc,
               SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) AS sal_pond_nom
        FROM fct_empregos
        WHERE id_municipio IN ('{IDS_SQL}') AND ano IN ({ANOS_EMPREGOS_SQL})
          AND descricao_cargo IS NOT NULL
        GROUP BY 1,2,3,4
    """).df()

    elig = c.execute(f"""
        SELECT id_municipio, ano, cbo_2002,
               SUM(CASE
                   WHEN ano=2020 AND salario_medio_reais >= {RENDA_MIN_POR_ANO[2020]} THEN total_vinculos
                   WHEN ano=2021 AND salario_medio_reais >= {RENDA_MIN_POR_ANO[2021]} THEN total_vinculos
                   WHEN ano=2022 AND salario_medio_reais >= {RENDA_MIN_POR_ANO[2022]} THEN total_vinculos
                   ELSE 0
               END) AS elegiveis_eq_2024
        FROM fct_empregos
        WHERE id_municipio IN ('{IDS_SQL}') AND ano IN ({ANOS_EMPREGOS_SQL})
        GROUP BY 1,2,3
    """).df()

    df = df.merge(elig, on=["id_municipio", "ano", "cbo_2002"], how="left")
    df["cidade"] = df["id_municipio"].map(CIDADES)
    df["fator_ipca_para_2024"] = df["ano"].map(FATORES)
    df["sal_pond_real_2024"] = (df["sal_pond_nom"] * df["fator_ipca_para_2024"]).round(0)
    df["pct_elegiveis"] = (df["elegiveis_eq_2024"] / df["vinc"].where(df["vinc"] > 0) * 100).round(2)
    df = df[[
        "cidade", "ano", "cbo_2002", "descricao_cargo",
        "vinc", "elegiveis_eq_2024", "pct_elegiveis",
        "sal_pond_nom", "sal_pond_real_2024", "fator_ipca_para_2024",
    ]].rename(columns={"vinc": "vinculos_total"})
    # filtra: cargos com pelo menos 1 vinculo elegivel em algum ano (mantem analise focada)
    cargos_com_eleg = df.groupby(["cidade", "cbo_2002"])["elegiveis_eq_2024"].sum().reset_index()
    cargos_com_eleg = cargos_com_eleg[cargos_com_eleg["elegiveis_eq_2024"] > 0][["cidade", "cbo_2002"]]
    df = df.merge(cargos_com_eleg, on=["cidade", "cbo_2002"])
    return df.sort_values(["cidade", "ano", "elegiveis_eq_2024"], ascending=[True, True, False])


# ============================================================
# Aba 6 - Cursos (concluintes) anual
# ============================================================
def aba_cursos(c):
    df = c.execute(f"""
        SELECT id_municipio, ano, nome_area_geral, nome_area_especifica, nome_area_detalhada,
               SUM(total_vagas)        AS total_vagas,
               SUM(total_ingressantes) AS total_ingressantes,
               SUM(total_matriculas)   AS total_matriculas,
               SUM(total_concluintes)  AS total_concluintes
        FROM fct_mercado_superior
        WHERE id_municipio IN ('{IDS_SQL}') AND ano BETWEEN 2020 AND 2024
        GROUP BY 1,2,3,4,5
        ORDER BY id_municipio, ano, total_concluintes DESC NULLS LAST
    """).df()
    df["cidade"] = df["id_municipio"].map(CIDADES)
    return df[[
        "cidade", "ano",
        "nome_area_geral", "nome_area_especifica", "nome_area_detalhada",
        "total_vagas", "total_ingressantes", "total_matriculas", "total_concluintes",
    ]]


# ============================================================
# Aba 7 - Cursos por IES anual
# ============================================================
def aba_ies(c):
    df = c.execute(f"""
        SELECT id_municipio, ano, nome_ies, rede, modalidade_ensino,
               nome_area_especifica, nome_area_detalhada,
               SUM(total_concluintes) AS total_concluintes,
               SUM(total_matriculas)  AS total_matriculas
        FROM fct_mercado_superior
        WHERE id_municipio IN ('{IDS_SQL}') AND ano BETWEEN 2020 AND 2024
        GROUP BY 1,2,3,4,5,6,7
    """).df()
    df["cidade"] = df["id_municipio"].map(CIDADES)
    return df[[
        "cidade", "ano", "nome_ies", "rede", "modalidade_ensino",
        "nome_area_especifica", "nome_area_detalhada",
        "total_matriculas", "total_concluintes",
    ]].sort_values(["cidade", "ano", "total_concluintes"], ascending=[True, True, False])


# ============================================================
# Aba 8 - Mercado potencial anual (resumo do que cresceu)
# ============================================================
def aba_mercado_potencial(kpis_df):
    pivot_eleg = kpis_df.pivot(index="cidade", columns="ano", values="elegiveis_eq_2024")
    pivot_eleg.columns = [f"eleg_{a}" for a in pivot_eleg.columns]
    pivot_eleg["delta_2020_2021_pct"] = ((pivot_eleg["eleg_2021"] - pivot_eleg["eleg_2020"]) / pivot_eleg["eleg_2020"] * 100).round(1)
    pivot_eleg["delta_2021_2022_pct"] = ((pivot_eleg["eleg_2022"] - pivot_eleg["eleg_2021"]) / pivot_eleg["eleg_2021"] * 100).round(1)
    pivot_eleg["delta_2020_2022_pct"] = ((pivot_eleg["eleg_2022"] - pivot_eleg["eleg_2020"]) / pivot_eleg["eleg_2020"] * 100).round(1)
    pivot_eleg = pivot_eleg.reset_index()

    pivot_sal = kpis_df.pivot(index="cidade", columns="ano", values="salario_eleg_medio_real_2024")
    pivot_sal.columns = [f"sal_eleg_real24_{a}" for a in pivot_sal.columns]
    pivot_sal = pivot_sal.reset_index()

    return pivot_eleg.merge(pivot_sal, on="cidade")


# ============================================================
# Aba 9 - Metadados (IPCA, parametros) + LEIA-ME
# ============================================================
def aba_meta():
    rows = []
    rows.append(("PARAMETROS", ""))
    rows.append(("Mensalidade alvo (R$)", MENSALIDADE))
    rows.append(("Affordability (% renda)", PCT_RENDA))
    rows.append(("Renda minima 2024 (R$)", round(RENDA_MIN_2024, 2)))
    rows.append(("", ""))
    rows.append(("IPCA / DEFLATOR", ""))
    rows.append(("Fonte", "IBGE/BCB serie 433 (acumulado anual)"))
    rows.append(("Logica", "Limiar de renda eh trazido a moeda nominal de cada ano para manter poder de compra de R$ 13.863 (2024). Salarios historicos sao mantidos em moeda nominal do ano + coluna adicional em moeda de 2024."))
    rows.append(("", ""))
    rows.append(("Ano", "IPCA % | Fator p/ 2024 | Limiar nominal (R$)"))
    for ano in [2020, 2021, 2022, 2023, 2024]:
        rows.append((str(ano), f"{IPCA_ANUAL[ano]}% | {round(FATORES[ano], 4)} | R$ {round(RENDA_MIN_POR_ANO[ano], 2)}"))
    rows.append(("", ""))
    rows.append(("COBERTURA POR FONTE (anos com buraco foram REMOVIDOS)", ""))
    rows.append(("fct_empregos (vinculos, cargos, salarios)", f"Anos mantidos: {ANOS_EMPREGOS}. Removidos 2023 e 2024 - vinculos cairam 60% (quebra de fonte: RAIS oficial vai ate 2022, 2023+ era fonte distinta com cobertura ~40%)."))
    rows.append(("fct_estabelecimentos (estabs)", f"Anos mantidos: {ANOS_ESTAB}. Removido 2022 - cobertura era 0.3% (Campinas 150 vs 51k em 2021)."))
    rows.append(("fct_mercado_superior (cursos, IES)", f"Anos mantidos: {ANOS_CURSOS}. Sem buracos identificados."))
    rows.append(("", ""))
    rows.append(("NOTAS DE ANALISE", ""))
    rows.append(("Aba 03_mercado_potencial",
                 "Pivot dos elegiveis_eq_2024 com deltas anuais 2020-2022. Use como referencia de tamanho de mercado em poder de compra constante."))
    rows.append(("Aba 06_mt_cargo_anual - filtro aplicado",
                 "Mantidos somente cargos com >=1 vinculo elegivel em algum ano (2020-2022). Salario por CBO eh ponderado e nao reflete dispersao intra-CBO."))
    rows.append(("Aba 05a / 05b - separacao de setores",
                 "Setores empregos (vinc, eleg, salario) em 05a com 2020-2022. Setores estabelecimentos (estabs, vinc_ativos) em 05b com 2020/2021/2023/2024. NAO sao combinaveis ano a ano."))
    rows.append(("Aba 07_cursos_anual / 08_ies_anual",
                 "Granularidade: area_geral > area_especifica > area_detalhada. Use area_detalhada pra filtrar cursos especificos (ex: MBA, Medicina, etc)."))
    return pd.DataFrame(rows, columns=["chave", "valor"])


# ============================================================
# Aba 9 - Score (3 dimensoes, normalizado em todo SP, igual ao dashboard)
#   D1 = Tamanho do Mercado Elegivel (40%)
#   D2 = Pipeline Academico (35%)
#   D3 = Dinamismo Economico (25%)
# ============================================================
def aba_score(c):
    ANO_RAIS = 2022  # ultimo ano limpo (vs dashboard que usa 2024)

    # D1a + D2a (escala mercado de trabalho) - todos municipios SP
    d1 = c.execute(f"""
        WITH v AS (
            SELECT id_municipio, SUM(total_vinculos) AS vinculos
            FROM fct_empregos WHERE ano = {ANO_RAIS}
            GROUP BY 1
        ),
        g AS (
            SELECT id_municipio, COUNT(DISTINCT cnpj) AS n_grandes
            FROM fct_empresas WHERE porte = '5' AND capital_social >= 1000000
            GROUP BY 1
        )
        SELECT d.id_municipio,
               COALESCE(v.vinculos, 0) AS vinculos,
               COALESCE(g.n_grandes, 0) AS n_grandes,
               COALESCE(g.n_grandes, 0) * 1000.0 / NULLIF(v.vinculos, 0) AS grandes_per_1k_vinc
        FROM dim_municipio d
        LEFT JOIN v ON v.id_municipio = d.id_municipio
        LEFT JOIN g ON g.id_municipio = d.id_municipio
        WHERE d.sigla_uf = 'SP'
    """).df()

    # D2: Pipeline academico
    d2 = c.execute(f"""
        WITH conc AS (
            SELECT id_municipio,
                   SUM(CASE WHEN nome_area_geral IN (
                        'Negocios, administracao e direito',
                        'Negócios, administração e direito',
                        'Tecnologias da informacao e comunicacao',
                        'Tecnologias da informação e comunicação',
                        'Engenharia, producao e construcao',
                        'Engenharia, produção e construção'
                   ) THEN total_concluintes ELSE 0 END) AS c_alvo,
                   SUM(CASE WHEN LOWER(rede) LIKE '%privad%' THEN total_concluintes ELSE 0 END) * 1.0
                       / NULLIF(SUM(total_concluintes), 0) AS pct_rede_privada,
                   SUM(total_concluintes) AS c_total
            FROM fct_mercado_superior
            WHERE sigla_uf = 'SP' AND ano = (SELECT MAX(ano) FROM fct_mercado_superior)
            GROUP BY 1
        )
        SELECT d.id_municipio,
               COALESCE(d.taxa_superior_25_mais, 0) AS taxa_sup_25mais,
               COALESCE(c.c_alvo, 0) * 1000.0 / NULLIF(d.populacao_total, 0) AS conc_alvo_per_1k_hab,
               COALESCE(c.pct_rede_privada, 0) AS pct_rede_privada,
               COALESCE(c.c_alvo, 0) AS conc_alvo_abs,
               COALESCE(c.c_total, 0) AS conc_total
        FROM dim_municipio d
        LEFT JOIN conc c ON c.id_municipio = d.id_municipio
        WHERE d.sigla_uf = 'SP'
    """).df()

    # D3: Dinamismo (IDHM + crescimento de vinculos 2020 -> 2022)
    d3 = c.execute(f"""
        WITH v0 AS (SELECT id_municipio, SUM(total_vinculos) AS v FROM fct_empregos WHERE ano = 2020 GROUP BY 1),
        v1 AS (SELECT id_municipio, SUM(total_vinculos) AS v FROM fct_empregos WHERE ano = {ANO_RAIS} GROUP BY 1)
        SELECT d.id_municipio,
               COALESCE(d.idhm, 0) AS idhm,
               CASE WHEN v0.v > 0 THEN (COALESCE(v1.v, 0) - v0.v) * 1.0 / v0.v ELSE NULL END AS crescimento_vinc_20_22
        FROM dim_municipio d
        LEFT JOIN v0 ON v0.id_municipio = d.id_municipio
        LEFT JOIN v1 ON v1.id_municipio = d.id_municipio
        WHERE d.sigla_uf = 'SP'
    """).df()

    base = c.execute("""
        SELECT id_municipio, nome_municipio, populacao_total
        FROM dim_municipio WHERE sigla_uf = 'SP'
    """).df()

    df = base.merge(d1, on="id_municipio", how="left") \
             .merge(d2, on="id_municipio", how="left") \
             .merge(d3, on="id_municipio", how="left")
    cols_fill = ["vinculos", "n_grandes", "grandes_per_1k_vinc", "taxa_sup_25mais",
                 "conc_alvo_per_1k_hab", "pct_rede_privada", "idhm", "crescimento_vinc_20_22",
                 "conc_alvo_abs", "conc_total"]
    df[cols_fill] = df[cols_fill].fillna(0)

    def norm(s):
        mn, mx = s.min(), s.max()
        return (s - mn) / (mx - mn + 1e-10)

    # Normalizacao - sub-indicadores
    df["n_vinculos"]            = norm(df["vinculos"])
    df["n_grandes_per_1k"]      = norm(df["grandes_per_1k_vinc"])
    df["n_taxa_sup"]            = norm(df["taxa_sup_25mais"])
    df["n_conc_alvo_per_1k"]    = norm(df["conc_alvo_per_1k_hab"])
    df["n_pct_privada"]         = norm(df["pct_rede_privada"])
    df["n_idhm"]                = norm(df["idhm"])
    df["n_crescimento"]         = norm(df["crescimento_vinc_20_22"])

    # Dimensoes consolidadas
    df["D1_mercado_elegivel"]   = ((df["n_vinculos"] + df["n_grandes_per_1k"]) / 2).round(4)
    df["D2_pipeline_academico"] = ((df["n_taxa_sup"] + df["n_conc_alvo_per_1k"] + df["n_pct_privada"]) / 3).round(4)
    df["D3_dinamismo"]          = ((df["n_idhm"] + df["n_crescimento"]) / 2).round(4)

    # Score final ponderado (40/35/25) na escala 0-100
    W = (0.40, 0.35, 0.25)
    df["score_0_100"] = (
        (df["D1_mercado_elegivel"] * W[0]
         + df["D2_pipeline_academico"] * W[1]
         + df["D3_dinamismo"] * W[2]) * 100
    ).round(2)

    # Ranks
    df["rank_SP"] = df["score_0_100"].rank(method="min", ascending=False).astype(int)

    # Filtra 4 pracas e rankeia entre elas
    df_4 = df[df["id_municipio"].isin(IDS)].copy()
    df_4["rank_4_pracas"] = df_4["score_0_100"].rank(method="min", ascending=False).astype(int)
    df_4["cidade"] = df_4["id_municipio"].map(CIDADES)

    cols_out = [
        "cidade", "score_0_100", "rank_4_pracas", "rank_SP",
        # D1
        "D1_mercado_elegivel", "vinculos", "n_grandes", "grandes_per_1k_vinc",
        # D2
        "D2_pipeline_academico", "taxa_sup_25mais", "conc_alvo_abs", "conc_alvo_per_1k_hab", "pct_rede_privada",
        # D3
        "D3_dinamismo", "idhm", "crescimento_vinc_20_22",
    ]
    df_4 = df_4[cols_out].sort_values("score_0_100", ascending=False)
    # arredondar
    for col in ["grandes_per_1k_vinc", "conc_alvo_per_1k_hab"]:
        df_4[col] = df_4[col].round(3)
    df_4["pct_rede_privada"] = (df_4["pct_rede_privada"] * 100).round(1)
    df_4["crescimento_vinc_20_22"] = (df_4["crescimento_vinc_20_22"] * 100).round(1)
    df_4["taxa_sup_25mais"] = df_4["taxa_sup_25mais"].round(2)
    return df_4


# ============================================================
# Aba 10 - Potencial de negocio
# ============================================================
def aba_potencial_negocio(c, df_score):
    PARCELAS = 36
    LTV_ALUNO = MENSALIDADE * PARCELAS  # R$ 47.412

    # Elegiveis 2022 por cidade
    limiar = RENDA_MIN_POR_ANO[2022]
    df_eleg = c.execute(f"""
        SELECT id_municipio,
               SUM(CASE WHEN salario_medio_reais >= {limiar} THEN total_vinculos ELSE 0 END) AS eleg
        FROM fct_empregos
        WHERE id_municipio IN ('{IDS_SQL}') AND ano = 2022
        GROUP BY 1
    """).df()
    df_eleg["cidade"] = df_eleg["id_municipio"].map(CIDADES)

    # SAM setorial - elegiveis em setores aderentes a MBA Executivo
    setores_alvo_like = [
        "Administra%P%blica%",
        "Com%rcio e Administra%",
        "Institui%es de Cr%dito%",
        "Ind%stria%",
        "Ensino",
        "Servi%os M%dicos%",
        "Transportes e Comunica%",
    ]
    where_clauses = " OR ".join([f"descricao_subsetor LIKE '{p}'" for p in setores_alvo_like])
    df_sam = c.execute(f"""
        SELECT id_municipio,
               SUM(CASE WHEN salario_medio_reais >= {limiar} THEN total_vinculos ELSE 0 END) AS eleg_setores_alvo
        FROM fct_empregos
        WHERE id_municipio IN ('{IDS_SQL}') AND ano = 2022
          AND ({where_clauses})
        GROUP BY 1
    """).df()

    df = df_eleg.merge(df_sam, on="id_municipio", how="left")
    df["pct_sam_no_tam"] = (df["eleg_setores_alvo"] / df["eleg"] * 100).round(1)

    # ============== Sheet final eh multi-bloco ==============
    blocos = []

    # ----- HEADER / PREMISSAS -----
    blocos.append(pd.DataFrame([
        ["PREMISSAS DO EXERCICIO", ""],
        ["Mensalidade (R$/mes)", MENSALIDADE],
        ["Parcelas (meses)", PARCELAS],
        ["Receita por aluno (LTV)", f"R$ {LTV_ALUNO:,.0f}"],
        ["Ano base elegiveis", 2022],
        ["Limiar de renda (R$ nominal 2022)", f"R$ {round(limiar, 0):,.0f}"],
        ["Limiar equivalente em R$ de 2024", f"R$ {RENDA_MIN_2024:,.2f}"],
        ["Affordability assumida", f"{PCT_RENDA}% da renda mensal"],
    ], columns=["item", "valor"]))

    # ----- BLOCO A: TAM por cidade -----
    blocos.append(pd.DataFrame([["", ""], ["BLOCO A - TAM (Total Addressable Market)", ""]],
                               columns=["item", "valor"]))
    df_tam = df.copy()
    df_tam["TAM_R$"] = (df_tam["eleg"] * LTV_ALUNO).round(0)
    df_tam = df_tam[["cidade", "eleg", "TAM_R$"]].rename(columns={"eleg": "elegiveis_2022"})
    df_tam_total = pd.DataFrame([{
        "cidade": "TOTAL 4 pracas",
        "elegiveis_2022": int(df_tam["elegiveis_2022"].sum()),
        "TAM_R$": int(df_tam["TAM_R$"].sum()),
    }])
    df_tam_full = pd.concat([df_tam, df_tam_total], ignore_index=True)
    blocos.append(df_tam_full)

    # ----- BLOCO B: Sensibilidade por penetracao -----
    blocos.append(pd.DataFrame([["", ""], ["BLOCO B - Sensibilidade: receita por % de penetracao do TAM", ""]],
                               columns=["item", "valor"]))
    penetracoes = [0.005, 0.01, 0.03, 0.05, 0.10, 0.15, 0.25]
    rows_b = []
    for _, r in df_tam.iterrows():
        row = {"cidade": r["cidade"], "elegiveis_2022": r["elegiveis_2022"], "TAM_R$": r["TAM_R$"]}
        for p in penetracoes:
            row[f"receita_{int(p*1000)/10}pct"] = round(r["TAM_R$"] * p, 0)
        rows_b.append(row)
    # linha total
    row_t = {"cidade": "TOTAL 4 pracas",
             "elegiveis_2022": df_tam["elegiveis_2022"].sum(),
             "TAM_R$": df_tam["TAM_R$"].sum()}
    for p in penetracoes:
        row_t[f"receita_{int(p*1000)/10}pct"] = round(df_tam["TAM_R$"].sum() * p, 0)
    rows_b.append(row_t)
    blocos.append(pd.DataFrame(rows_b))

    # ----- BLOCO C: Engenharia reversa da meta -----
    blocos.append(pd.DataFrame([["", ""], ["BLOCO C - Engenharia reversa: quantos alunos para atingir meta de receita", ""]],
                               columns=["item", "valor"]))
    metas = [1_000_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000, 100_000_000]
    rows_c = []
    for meta in metas:
        alunos_necessarios = int(round(meta / LTV_ALUNO))
        row = {"meta_R$": meta, "alunos_necessarios_total": alunos_necessarios}
        for _, r in df_tam.iterrows():
            pct_do_tam = round(meta / r["TAM_R$"] * 100, 2) if r["TAM_R$"] else None
            row[f"{r['cidade']}_pct_do_TAM"] = pct_do_tam
        rows_c.append(row)
    blocos.append(pd.DataFrame(rows_c))

    # ----- BLOCO D: SAM setorial -----
    blocos.append(pd.DataFrame([["", ""], ["BLOCO D - SAM (filtro setorial: setores aderentes a MBA Executivo)", ""],
                                ["Setores incluidos", "Adm.Publica + Comercio/Imoveis/Serv.Tecnicos + Cred./Seguros + Industrias + Ensino + Serv.Medicos + Transp./Com."]],
                               columns=["item", "valor"]))
    df_sam_out = df.copy()
    df_sam_out["SAM_R$"] = (df_sam_out["eleg_setores_alvo"] * LTV_ALUNO).round(0)
    df_sam_out["TAM_R$"] = (df_sam_out["eleg"] * LTV_ALUNO).round(0)
    df_sam_out = df_sam_out[["cidade", "eleg", "eleg_setores_alvo", "pct_sam_no_tam", "TAM_R$", "SAM_R$"]] \
        .rename(columns={"eleg": "elegiveis_2022_TAM", "eleg_setores_alvo": "elegiveis_2022_setores_alvo"})
    blocos.append(df_sam_out)

    # ----- BLOCO F: Score x TAM (priorizacao) -----
    blocos.append(pd.DataFrame([["", ""], ["BLOCO F - Priorizacao: TAM x Score (onde a proxima parcela de investimento rende mais)", ""],
                                ["Formula", "TAM_R$ * (score_0_100 / 100)"]],
                               columns=["item", "valor"]))
    df_score_only = df_score[["cidade", "score_0_100", "rank_4_pracas"]]
    df_f = df_tam.merge(df_score_only, on="cidade")
    df_f["TAM_x_score"] = (df_f["TAM_R$"] * df_f["score_0_100"] / 100).round(0)
    df_f["rank_prioridade"] = df_f["TAM_x_score"].rank(method="min", ascending=False).astype(int)
    df_f = df_f[["cidade", "elegiveis_2022", "TAM_R$", "score_0_100", "TAM_x_score", "rank_prioridade", "rank_4_pracas"]] \
        .sort_values("TAM_x_score", ascending=False)
    blocos.append(df_f)

    return blocos


# ============================================================
# Aba 11 - Metodologia
# ============================================================
def aba_metodologia():
    rows = [
        # === Parametros ===
        ("PARAMETROS DO ESTUDO", "", "", "", "", ""),
        ("Mensalidade alvo", "-", f"R$ {MENSALIDADE:.2f}/mes - premissa de produto", "-", "Premissa de negocio", "Pode mudar se ticket evoluir"),
        ("Affordability", "-", f"{PCT_RENDA}% da renda mensal -> renda minima R$ {RENDA_MIN_2024:,.2f}/mes", "-", "Premissa de negocio", "Usado para definir 'elegivel'"),
        ("LTV por aluno", "-", f"{MENSALIDADE} x 36 parcelas = R$ {MENSALIDADE*36:,.0f}", "-", "Premissa de negocio", "Sem desconto de evasao/inadimplencia"),
        ("Fator IPCA (deflator)", "-", "Acumulado ano X -> 2024, serie 433 do BCB (IPCA anual)", "2020-2024", "IBGE/BCB", "Inflacionar o limiar de renda do ano X mantem poder de compra constante em R$ 13.863 (2024)"),

        # === Aba 01 - Socio ===
        ("", "", "", "", "", ""),
        ("Aba 01_socioeconomico", "", "", "", "", ""),
        ("Pop. 25+ com superior completo (%)", "dim_municipio", "Campo taxa_superior_25_mais", "Censo 2010 + projecao", "IBGE (Censo + PNAD-C)", "Estimativa censitaria; nao atualiza ano a ano"),
        ("Pop. 25+ com superior completo (absoluto)", "dim_municipio", "populacao_total * taxa_superior_25_mais / 100", "Censo 2010 + projecao", "IBGE", "Calculado a partir do % - aproximacao"),
        ("Renda per capita", "dim_municipio", "Campo renda_per_capita (mensal, R$ nominal Censo)", "Censo 2010", "IBGE", "Defasagem temporal - foto do Censo, nao corrigido por IPCA"),
        ("IDHM geral", "dim_municipio", "Campo idhm", "2010 (atualizacao parcial)", "PNUD/IBGE", "Indice composto 0-1"),
        ("Indice de Gini", "dim_municipio", "Campo indice_gini", "Censo 2010", "IBGE", "0=igualdade total, 1=desigualdade maxima"),
        ("Proporcao em pobreza (%)", "dim_municipio", "Campo prop_pobreza", "Censo 2010", "IBGE", "Linha de pobreza nacional"),
        ("Renda media RAIS", "fct_empregos", "Σ(total_vinculos × salario_medio_reais) / Σ(total_vinculos) | filtro ano=2022", "2022", "RAIS (Min. Trabalho)", "Ponderado por num. de vinculos, nao por pessoa fisica. Subestima trabalhadores informais."),
        ("% elegiveis", "fct_empregos", "vinculos com salario >= R$ 12.640 (limiar 2022 deflacionado) / total vinculos", "2022", "RAIS", "Limiar mantem poder de compra = R$ 13.863 (2024)"),
        ("Qtd elegiveis (absoluto)", "fct_empregos", "Σ vinculos com salario >= R$ 12.640 (limiar 2022)", "2022", "RAIS", "Conta vinculos, nao pessoas fisicas (uma pessoa pode ter +1 vinculo)"),
        ("Renda media dos elegiveis", "fct_empregos", "media ponderada do salario apenas para vinculos com salario >= limiar do ano", "2022", "RAIS", "Indicador do teto medio dos pagantes potenciais"),

        # === Aba 02 - MT KPIs ===
        ("", "", "", "", "", ""),
        ("Aba 02_mt_kpis_anual", "", "", "", "", ""),
        ("vinculos_total", "fct_empregos", "Σ total_vinculos por (cidade, ano)", "2020-2022", "RAIS", "RAIS apos 2022 tem quebra de cobertura - removida"),
        ("elegiveis_eq_2024", "fct_empregos", "Σ vinculos com salario >= limiar_nominal_do_ano (deflacionado p/ R$ 13.863 de 2024)", "2020-2022", "RAIS", "Mantem poder de compra constante. Ex: 2020 limiar = R$ 10.856 nominal"),
        ("pct_elegiveis", "fct_empregos", "elegiveis_eq_2024 / vinculos_total × 100", "2020-2022", "Calculado", "-"),
        ("salario_medio_pond_nominal", "fct_empregos", "Σ(vinc × sal) / Σ vinc - sem deflator", "2020-2022", "RAIS", "Em reais nominais de cada ano"),
        ("salario_medio_pond_real_2024", "fct_empregos + IPCA", "salario_medio_pond_nominal × fator_IPCA(ano->2024)", "2020-2022 em R$ de 2024", "Calculado", "Permite comparar evolucao real (sem ilusao monetaria)"),

        # === Aba 03 - Mercado potencial ===
        ("", "", "", "", "", ""),
        ("Aba 03_mercado_potencial", "", "", "", "", ""),
        ("eleg_2020 / 2021 / 2022", "fct_empregos", "Pivot dos elegiveis_eq_2024 - em moeda nominal de cada ano com limiar deflacionado", "2020-2022", "RAIS", "Equivale em poder de compra a R$ 13.863 hoje"),
        ("delta_20_22_pct", "Calculado", "(eleg_2022 - eleg_2020) / eleg_2020 × 100", "2020-2022", "Calculado", "Crescimento do mercado potencial nesses anos"),

        # === Aba 04 - Estab ===
        ("", "", "", "", "", ""),
        ("Aba 04_estab_anual", "", "", "", "", ""),
        ("estabelecimentos", "fct_estabelecimentos", "Σ total_estabelecimentos por (cidade, ano)", "2020, 2021, 2023, 2024", "RAIS", "Ano 2022 removido - cobertura era 0,3% (incompleta)"),
        ("vinculos_ativos", "fct_estabelecimentos", "Σ total_vinculos_ativos", "2020, 2021, 2023, 2024", "RAIS", "Diferenciar de vinculos (fct_empregos): aqui eh estoque ativo"),

        # === Aba 05 - Setores ===
        ("", "", "", "", "", ""),
        ("Aba 05a_setor_empregos / 05b_setor_estabs", "", "", "", "", ""),
        ("descricao_subsetor", "fct_empregos / fct_estabelecimentos", "Subsetor IBGE (25 categorias)", "2020-2022 / 2020-21-23-24", "Classificacao IBGE", "Granularidade mais agregada - use CBO/CNAE pra cortar mais fino"),

        # === Aba 06 - Cargos ===
        ("", "", "", "", "", ""),
        ("Aba 06_mt_cargo_anual", "", "", "", "", ""),
        ("cbo_2002 / descricao_cargo", "fct_empregos", "CBO 6 digitos (Classificacao Brasileira de Ocupacoes 2002)", "2020-2022", "Min. Trabalho", "Mais de 2.500 ocupacoes possiveis. Filtramos so as com >=1 vinculo elegivel"),
        ("sal_pond_nom / sal_pond_real_2024", "fct_empregos", "Salario medio ponderado dentro do CBO, com versao deflacionada", "2020-2022", "RAIS + IPCA", "Ponderado por vinculo nao reflete dispersao intra-CBO"),

        # === Aba 07 - Cursos ===
        ("", "", "", "", "", ""),
        ("Aba 07_cursos_anual / 08_ies_anual", "", "", "", "", ""),
        ("total_concluintes", "fct_mercado_superior", "Σ alunos formados no ano", "2020-2024", "INEP - Censo da Educacao Superior", "Inclui presencial e EAD"),
        ("total_matriculas", "fct_mercado_superior", "Σ alunos matriculados no ano (estoque)", "2020-2024", "INEP", "-"),
        ("total_ingressantes", "fct_mercado_superior", "Σ entrada no ano", "2020-2024", "INEP", "Util para projetar concluintes futuros (4-5 anos pra frente)"),
        ("nome_area_geral/especifica/detalhada", "fct_mercado_superior", "Classificacao OECD CINE 2013 em 3 niveis", "2020-2024", "INEP (mapeada para CINE)", "Detalhada eh a mais fina"),

        # === Aba 09 - Score ===
        ("", "", "", "", "", ""),
        ("Aba 09_score", "", "", "", "", ""),
        ("D1 - Tamanho do Mercado Elegivel", "fct_empregos + fct_empresas", "media de 2 sub-indicadores normalizados (min-max em todo SP): total de vinculos + empresas porte 5 com cap>=R$1M por 1k vinculos", "2022", "RAIS + Receita Federal/CNPJ", "Peso 40% no score final"),
        ("D2 - Pipeline Academico", "dim_municipio + fct_mercado_superior", "media de 3 sub-ind normalizados: taxa_superior_25_mais + concluintes em areas-alvo (Negocios/TIC/Eng) por 1k habitantes + % rede privada", "2022/2024", "IBGE + INEP", "Peso 35% no score final. Areas-alvo: filtragem aderente a portfolio MBA"),
        ("D3 - Dinamismo Economico", "dim_municipio + fct_empregos", "media de 2 sub-ind normalizados: IDHM + crescimento de vinculos 2020->2022", "2022", "IBGE/PNUD + RAIS", "Peso 25%. Divergencia vs dashboard: dashboard usa cresc 2020->2024 (com fonte quebrada); aqui usamos 2020->2022 (RAIS limpa)"),
        ("score_0_100", "Calculado", "(D1×0.40 + D2×0.35 + D3×0.25) × 100", "-", "Calculado", "Pesos default do dashboard. 0=pior, 100=melhor"),
        ("rank_SP", "Calculado", "Posicao no universo de 645 municipios SP", "-", "Calculado", "1 = melhor de SP"),

        # === Aba 10 - Potencial de negocio ===
        ("", "", "", "", "", ""),
        ("Aba 10_potencial_negocio", "", "", "", "", ""),
        ("TAM (Total Addressable Market)", "fct_empregos", "elegiveis_2022 × LTV (R$ 47.412)", "2022", "RAIS + Premissa", "Ceiling absoluto - assume 100% de captura e 0 evasao"),
        ("Penetracao", "Premissa", "% do TAM efetivamente capturado", "-", "Premissa", "Sensibilidade pra modelar cenarios. Benchmark mercado pos-graduacao FGV-IBE: ~3-8% nas suas pracas atuais"),
        ("SAM (Serviceable Available Market)", "fct_empregos filtrado", "elegiveis_2022 apenas em setores aderentes a MBA Executivo", "2022", "RAIS", "Setores: Adm.Pub + Comercio/Imoveis + Cred./Seguros + Industrias + Ensino + Serv.Medicos + Transp./Com."),
        ("TAM × Score (priorizacao)", "Calculado", "TAM_R$ × (score / 100) = potencial absoluto ajustado pela atratividade", "-", "Calculado", "Util pra responder 'em qual praca o proximo R$ rende mais'"),
    ]
    return pd.DataFrame(rows, columns=["KPI", "Tabela no BD", "Calculo", "Ano referencia", "Fonte primaria", "Caveats / Notas"])


def aplicar_formatacao(out_path):
    """Largura de colunas, freeze panes e formato numero."""
    from openpyxl import load_workbook
    wb = load_workbook(out_path)
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        # autosize aproximado
        for col in ws.columns:
            max_len = 0
            letter = col[0].column_letter
            for cell in col:
                try:
                    v = str(cell.value) if cell.value is not None else ""
                    if len(v) > max_len:
                        max_len = len(v)
                except Exception:
                    pass
            ws.column_dimensions[letter].width = min(max(12, max_len + 2), 60)
    wb.save(out_path)


# ============================================================
# Main
# ============================================================
def main():
    c = conn()
    print("Aba 1...")
    df_socio = aba_socioeconomico(c)
    print("Aba 2...")
    df_kpis = aba_mt_kpis(c)
    print("Aba 3...")
    df_estab = aba_estab(c)
    print("Aba 4...")
    df_setores_emp = aba_setores_empregos(c)
    df_setores_est = aba_setores_estabs(c)
    print("Aba 5...")
    df_cargos = aba_cargos(c)
    print("Aba 6...")
    df_cursos = aba_cursos(c)
    print("Aba 7...")
    df_ies = aba_ies(c)
    print("Aba 8...")
    df_mp = aba_mercado_potencial(df_kpis)
    print("Aba score...")
    df_score = aba_score(c)
    print("Aba potencial negocio...")
    blocos_pn = aba_potencial_negocio(c, df_score)
    print("Aba metodologia...")
    df_metodologia = aba_metodologia()
    print("Aba 9...")
    df_meta = aba_meta()
    c.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"Escrevendo {OUT}...")
    with pd.ExcelWriter(OUT, engine="openpyxl") as w:
        df_meta.to_excel(w, sheet_name="00_metadados", index=False)
        df_socio.to_excel(w, sheet_name="01_socioeconomico", index=False)
        df_kpis.to_excel(w, sheet_name="02_mt_kpis_anual", index=False)
        df_mp.to_excel(w, sheet_name="03_mercado_potencial", index=False)
        df_estab.to_excel(w, sheet_name="04_estab_anual", index=False)
        df_setores_emp.to_excel(w, sheet_name="05a_setor_empregos", index=False)
        df_setores_est.to_excel(w, sheet_name="05b_setor_estabs", index=False)
        df_cargos.to_excel(w, sheet_name="06_mt_cargo_anual", index=False)
        df_cursos.to_excel(w, sheet_name="07_cursos_anual", index=False)
        df_ies.to_excel(w, sheet_name="08_ies_anual", index=False)
        df_score.to_excel(w, sheet_name="09_score", index=False)

        # Aba 10: multi-bloco - escreve sequencialmente
        ws_row = 0
        for bloco in blocos_pn:
            bloco.to_excel(w, sheet_name="10_potencial_negocio", index=False, startrow=ws_row, header=True)
            ws_row += len(bloco) + 2  # gap

        df_metodologia.to_excel(w, sheet_name="11_metodologia", index=False)

    aplicar_formatacao(OUT)
    print("OK")
    print(f"  socio:        {len(df_socio)}")
    print(f"  kpis:         {len(df_kpis)}")
    print(f"  estab:        {len(df_estab)}")
    print(f"  setor_emp:    {len(df_setores_emp)}")
    print(f"  setor_estab:  {len(df_setores_est)}")
    print(f"  cargos:       {len(df_cargos)}")
    print(f"  cursos:       {len(df_cursos)}")
    print(f"  ies:          {len(df_ies)}")


if __name__ == "__main__":
    main()
