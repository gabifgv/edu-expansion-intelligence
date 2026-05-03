import duckdb, urllib.request, json

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

# ── Parâmetros (entradas do usuário no dashboard) ────────────────────────────
id_municipio        = "3509502"   # selecionado pelo usuário
cep_gestora         = "13051093"  # digitado pelo usuário (aceita com ou sem hífen)
setor_filtro        = None        # None = todos; filtro multi-select no dashboard
capital_social_min  = 500_000     # R$ — filtra SPEs e holdings vazias; padrão R$ 500K

# ── Geocodifica CEP da gestora ────────────────────────────────────────────────
def geocodificar_cep(cep):
    cep = cep.replace("-", "")
    try:
        req = urllib.request.Request(
            f"https://brasilapi.com.br/api/cep/v2/{cep}",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
        lat = d.get("location", {}).get("coordinates", {}).get("latitude")
        lon = d.get("location", {}).get("coordinates", {}).get("longitude")
        if lat and lon:
            return float(lat), float(lon), d.get("street", "")
    except Exception:
        pass
    row = con.execute(f"SELECT latitude, longitude FROM dim_cep_coords WHERE cep='{cep}'").fetchone()
    if row:
        return row[0], row[1], "(coords via DuckDB)"
    return None, None, "CEP nao encontrado"

lat_g, lon_g, rua_g = geocodificar_cep(cep_gestora)

print(f"=== BLOCO 4: Empresas-Alvo — Campinas/SP ===")
print(f"CEP referencia: {cep_gestora} | {rua_g}")
print(f"Coords: lat={lat_g:.6f}, lon={lon_g:.6f}\n")

if lat_g is None:
    print("ERRO: nao foi possivel geocodificar o CEP da gestora.")
    con.close()
    exit()

# ── Lookup cnae_classe → setor (mais frequente por vinculos) ─────────────────
filtro_setor = f"AND sl.descricao_subsetor = '{setor_filtro}'" if setor_filtro else ""

df = con.execute(f"""
    WITH setor_base AS (
        SELECT cnae_classe, descricao_subsetor, SUM(total_vinculos) AS v
        FROM fct_empregos
        WHERE cnae_classe IS NOT NULL
        GROUP BY 1, 2
    ),
    setor_lookup AS (
        SELECT DISTINCT ON (cnae_classe) cnae_classe, descricao_subsetor
        FROM setor_base
        ORDER BY cnae_classe, v DESC
    )
    SELECT
        e.nome_empresa,
        COALESCE(sl.descricao_subsetor, 'Nao Classificado') AS setor,
        e.cep,
        COALESCE('(' || e.ddd || ') ' || e.telefone, '-')   AS contato_fone,
        COALESCE(e.email, '-')                               AS contato_email,
        ROUND(
            2 * 6371 * ASIN(SQRT(
                POWER(SIN(RADIANS(c.latitude  - {lat_g}) / 2), 2) +
                COS(RADIANS({lat_g})) * COS(RADIANS(c.latitude)) *
                POWER(SIN(RADIANS(c.longitude - {lon_g}) / 2), 2)
            ))
        , 2) AS distancia_km
    FROM fct_empresas e
    JOIN dim_cep_coords c ON c.cep = e.cep
    LEFT JOIN setor_lookup sl ON sl.cnae_classe = e.cnae_classe
    WHERE e.id_municipio = '{id_municipio}'
      AND e.porte = '5'
      AND e.capital_social >= {capital_social_min}
      {filtro_setor}
    ORDER BY distancia_km
    LIMIT 30
""").df()

total = con.execute(f"""
    WITH setor_base AS (
        SELECT cnae_classe, descricao_subsetor, SUM(total_vinculos) AS v
        FROM fct_empregos WHERE cnae_classe IS NOT NULL GROUP BY 1, 2
    ),
    setor_lookup AS (
        SELECT DISTINCT ON (cnae_classe) cnae_classe, descricao_subsetor
        FROM setor_base ORDER BY cnae_classe, v DESC
    )
    SELECT COUNT(*) FROM fct_empresas e
    JOIN dim_cep_coords c ON c.cep = e.cep
    LEFT JOIN setor_lookup sl ON sl.cnae_classe = e.cnae_classe
    WHERE e.id_municipio = '{id_municipio}' AND e.porte = '5'
      AND e.capital_social >= {capital_social_min}
    {filtro_setor}
""").fetchone()[0]

print(f"Capital social minimo: R$ {capital_social_min:,.0f}")
print(f"Total empresas elegíveis com coords: {total:,} | Exibindo top 30 por proximidade\n")
print(f"{'Empresa':<45} {'Setor':<35} {'CEP':>9} {'Dist.':>7} {'Telefone':>16} {'Email'}")
print("-" * 140)
for _, r in df.iterrows():
    print(f"  {str(r['nome_empresa'])[:45]:<45} {str(r['setor'])[:35]:<35} "
          f"{str(r['cep']):>9} {float(r['distancia_km']):>6.1f}km "
          f"{str(r['contato_fone']):>16}  {str(r['contato_email'])[:40]}")

con.close()
