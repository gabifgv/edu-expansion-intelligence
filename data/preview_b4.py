import duckdb, urllib.request, json, webbrowser, os

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

id_municipio       = "3509502"
cep_gestora        = "13051093"
capital_social_min = 500_000   # R$ — padrão sugerido; entrada do usuário no dashboard

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

df = con.execute(f"""
    WITH setor_base AS (
        SELECT cnae_classe, descricao_subsetor, SUM(total_vinculos) AS v
        FROM fct_empregos WHERE cnae_classe IS NOT NULL GROUP BY 1, 2
    ),
    setor_lookup AS (
        SELECT DISTINCT ON (cnae_classe) cnae_classe, descricao_subsetor
        FROM setor_base ORDER BY cnae_classe, v DESC
    )
    SELECT
        e.nome_empresa,
        COALESCE(sl.descricao_subsetor, 'Nao Classificado') AS setor,
        e.cep,
        c.latitude,
        c.longitude,
        e.capital_social,
        COALESCE('(' || e.ddd || ') ' || e.telefone, '-')   AS contato_fone,
        COALESCE(e.email, '-')                               AS contato_email,
        ROUND(
            2 * 6371 * ASIN(SQRT(
                POWER(SIN(RADIANS(c.latitude  - {lat_g}) / 2), 2) +
                COS(RADIANS({lat_g})) * COS(RADIANS(c.latitude)) *
                POWER(SIN(RADIANS(c.longitude - {lon_g}) / 2), 2)
            ))
        , 2) AS dist_reta
    FROM fct_empresas e
    JOIN dim_cep_coords c ON c.cep = e.cep
    LEFT JOIN setor_lookup sl ON sl.cnae_classe = e.cnae_classe
    WHERE e.id_municipio = '{id_municipio}' AND e.porte = '5'
      AND e.capital_social >= {capital_social_min}
    ORDER BY dist_reta
    LIMIT 150
""").df()
con.close()

# ── Distância de carro via OSRM (em lotes de 99 destinos) ────────────────────
def osrm_distances(lat_o, lon_o, coords, batch=99):
    results = []
    for i in range(0, len(coords), batch):
        chunk = coords[i:i+batch]
        waypts = f"{lon_o},{lat_o}" + "".join(f";{lon},{lat}" for lat, lon in chunk)
        url = (f"http://router.project-osrm.org/table/v1/driving/{waypts}"
               f"?sources=0&annotations=distance")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            row = data["distances"][0]
            results.extend([d / 1000 if d is not None else None for d in row[1:]])
        except Exception as e:
            print(f"  OSRM lote {i//batch+1} falhou ({e}), usando linha reta")
            results.extend([None] * len(chunk))
    return results

print(f"Calculando distancias de carro (OSRM) para {len(df)} empresas...")
coords = list(zip(df["latitude"], df["longitude"]))
driving = osrm_distances(lat_g, lon_g, coords)

df["distancia_km"] = [
    round(d, 1) if d is not None else float(r["dist_reta"])
    for d, (_, r) in zip(driving, df.iterrows())
]
df = df.sort_values("distancia_km").reset_index(drop=True)
print(f"Top 3 distancias: {list(df['distancia_km'][:3])}")

# ── Formata capital social ────────────────────────────────────────────────────
def fmt_capital(v):
    if v is None or v == 0:
        return ("-", 0)
    v = float(v)
    if v >= 1_000_000:
        label = f"R$ {v/1_000_000:.1f}M"
    elif v >= 1_000:
        label = f"R$ {v/1_000:.0f}K"
    else:
        label = f"R$ {v:.0f}"
    return (label, v)

setores = sorted(df["setor"].dropna().unique().tolist())

rows_json = []
for _, r in df.iterrows():
    cap_label, cap_val = fmt_capital(r["capital_social"])
    rows_json.append({
        "nome":    str(r["nome_empresa"])[:60],
        "setor":   str(r["setor"]),
        "cep":     str(r["cep"]),
        "capital": cap_label,
        "cap_val": cap_val,
        "fone":    str(r["contato_fone"]),
        "email":   str(r["contato_email"])[:55],
        "dist":    float(r["distancia_km"]),
    })

rows_json_str = json.dumps(rows_json, ensure_ascii=False)
setor_opts    = "".join(f'<option value="{s}">{s}</option>' for s in setores)

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Bloco 4 — Empresas-Alvo</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f172a; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 24px; }}
  h2 {{ color: #38bdf8; margin-bottom: 6px; font-size: 1.3rem; }}
  .meta {{ color: #94a3b8; font-size: 0.81rem; margin-bottom: 8px; }}
  .meta span {{ color: #e2e8f0; }}
  .aviso {{
    display: inline-block; background: #172033; border: 1px solid #1e4060;
    color: #7dd3fc; border-radius: 6px; padding: 5px 12px;
    font-size: 0.78rem; margin-bottom: 20px;
  }}
  .controls {{ display: flex; gap: 16px; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; }}
  .controls label {{ color: #94a3b8; font-size: 0.78rem; display: block; margin-bottom: 4px; }}
  select, input[type=text] {{
    background: #1e293b; border: 1px solid #334155; color: #e2e8f0;
    border-radius: 6px; padding: 6px 10px; font-size: 0.82rem; outline: none;
  }}
  select:focus, input:focus {{ border-color: #38bdf8; }}
  select[multiple] {{ height: 140px; min-width: 260px; }}
  .btn {{
    background: #0ea5e9; color: #0f172a; border: none;
    border-radius: 6px; padding: 6px 14px; font-size: 0.82rem;
    cursor: pointer; font-weight: 600; align-self: flex-end;
  }}
  .btn:hover {{ background: #38bdf8; }}

  .card {{ background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  thead th {{
    color: #94a3b8; text-transform: uppercase; letter-spacing: .05em;
    font-size: 0.72rem; padding: 8px 10px; text-align: left;
    border-bottom: 1px solid #334155; white-space: nowrap;
    cursor: pointer; user-select: none;
  }}
  thead th:hover {{ color: #e2e8f0; }}
  thead th.active {{ color: #38bdf8; }}
  thead th.right {{ text-align: right; }}
  .sort-arrow {{ margin-left: 4px; opacity: .5; }}
  .sort-arrow.on {{ opacity: 1; color: #38bdf8; }}
  tbody tr {{ border-bottom: 1px solid #1e2d3d; transition: background .15s; }}
  tbody tr:hover {{ background: #243044; }}
  td {{ padding: 9px 10px; vertical-align: middle; }}
  td.right {{ text-align: right; }}
  .dist-verde   {{ color: #34d399; font-weight: 600; }}
  .dist-amarelo {{ color: #fbbf24; font-weight: 600; }}
  .dist-vermelho{{ color: #f87171; font-weight: 600; }}
  .setor-badge {{
    display: inline-block; background: #0f2137; color: #7dd3fc;
    border-radius: 4px; padding: 2px 8px; font-size: 0.75rem;
    border: 1px solid #1e4060;
  }}
  .capital {{ color: #a78bfa; font-weight: 500; font-size: 0.8rem; }}
  .email {{ color: #94a3b8; font-size: 0.78rem; }}

  /* Paginação */
  .pag {{ display: flex; gap: 6px; align-items: center; margin-top: 14px; flex-wrap: wrap; }}
  .pag-btn {{
    background: #1e293b; border: 1px solid #334155; color: #94a3b8;
    border-radius: 5px; padding: 4px 10px; font-size: 0.8rem; cursor: pointer;
  }}
  .pag-btn:hover {{ border-color: #38bdf8; color: #e2e8f0; }}
  .pag-btn.active {{ background: #0ea5e9; border-color: #0ea5e9; color: #0f172a; font-weight: 700; cursor: default; }}
  .pag-btn.nav {{ padding: 4px 8px; }}
  .pag-info {{ color: #64748b; font-size: 0.78rem; margin-left: 6px; }}
</style>
</head>
<body>

<h2>Bloco 4 — Empresas-Alvo</h2>
<p class="meta">
  Referência: <span>{cep_gestora[:5]}-{cep_gestora[5:]}</span> ({rua_g}) &nbsp;·&nbsp;
  Distâncias de carro via OSRM (rotas reais)
</p>
<div class="aviso">
  Empresas fora do regime Simples/MEI/EPP (porte "Demais" na Receita Federal) &nbsp;·&nbsp;
  Capital Social = valor declarado na RFB — proxy de porte financeiro; exclui SPEs e holdings vazias
</div>

<div class="controls">
  <div>
    <label>Capital Social mínimo</label>
    <select id="cap-min">
      <option value="0">Qualquer valor</option>
      <option value="100000">Acima de R$ 100K</option>
      <option value="500000" selected>Acima de R$ 500K</option>
      <option value="1000000">Acima de R$ 1M</option>
      <option value="2000000">Acima de R$ 2M</option>
      <option value="5000000">Acima de R$ 5M</option>
      <option value="10000000">Acima de R$ 10M</option>
    </select>
  </div>
  <div>
    <label>Filtrar por setor (Ctrl+clique para múltiplos)</label>
    <select id="setor-filter" multiple>{setor_opts}</select>
  </div>
  <div>
    <label>Buscar empresa</label>
    <input type="text" id="search" placeholder="nome da empresa..." style="width:200px">
  </div>
  <button class="btn" onclick="clearFilters()">Limpar filtros</button>
</div>

<div class="card">
  <table>
    <thead id="thead">
      <tr>
        <th style="width:30px">#</th>
        <th onclick="sortBy('nome')"  data-col="nome">Empresa <span class="sort-arrow" id="arr-nome"></span></th>
        <th onclick="sortBy('setor')" data-col="setor">Setor <span class="sort-arrow" id="arr-setor"></span></th>
        <th onclick="sortBy('cap_val')" data-col="cap_val" class="right">Capital Social <span class="sort-arrow" id="arr-cap_val"></span></th>
        <th>CEP</th>
        <th onclick="sortBy('dist')" data-col="dist" class="right">Distância ▼ <span class="sort-arrow on" id="arr-dist">▲</span></th>
        <th>Telefone</th>
        <th>E-mail</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="pag" id="pagination"></div>
</div>

<script>
const ALL = {rows_json_str};
const PAGE = 15;
let page = 1, col = 'dist', dir = 1, filtered = [];

function distClass(d) {{
  return d <= 5 ? 'dist-verde' : d <= 15 ? 'dist-amarelo' : 'dist-vermelho';
}}
function fmtCep(c) {{
  return c.length === 8 ? c.slice(0,5)+'-'+c.slice(5) : c;
}}

function sortBy(c) {{
  if (col === c) {{ dir *= -1; }} else {{ col = c; dir = 1; }}
  page = 1;
  render();
}}

function render() {{
  const sel = Array.from(document.getElementById('setor-filter').selectedOptions).map(o => o.value);
  const q   = document.getElementById('search').value.toLowerCase().trim();

  const capMin = parseFloat(document.getElementById('cap-min').value) || 0;

  filtered = ALL.filter(r => {{
    if (r.cap_val < capMin) return false;
    if (sel.length && !sel.includes(r.setor)) return false;
    if (q && !r.nome.toLowerCase().includes(q)) return false;
    return true;
  }});

  filtered.sort((a, b) => {{
    const va = a[col], vb = b[col];
    if (typeof va === 'string') return dir * va.localeCompare(vb, 'pt');
    return dir * (va - vb);
  }});

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE));
  page = Math.min(page, totalPages);
  const slice = filtered.slice((page-1)*PAGE, page*PAGE);
  const offset = (page-1)*PAGE;

  document.getElementById('tbody').innerHTML = slice.map((r, i) => `
    <tr>
      <td style="color:#64748b">${{offset+i+1}}</td>
      <td style="font-weight:500;max-width:240px">${{r.nome}}</td>
      <td><span class="setor-badge">${{r.setor}}</span></td>
      <td class="right capital">${{r.capital}}</td>
      <td style="color:#94a3b8;white-space:nowrap">${{fmtCep(r.cep)}}</td>
      <td class="right ${{distClass(r.dist)}}" style="white-space:nowrap">${{r.dist.toFixed(1)}} km</td>
      <td style="white-space:nowrap">${{r.fone}}</td>
      <td class="email">${{r.email==='-'?'<span style=color:#475569>—</span>':r.email}}</td>
    </tr>`).join('');

  // arrows
  ['nome','setor','cap_val','dist'].forEach(c => {{
    const el = document.getElementById('arr-'+c);
    if (!el) return;
    el.className = 'sort-arrow' + (col===c?' on':'');
    el.textContent = col===c ? (dir===1?'▲':'▼') : '';
  }});

  // pagination
  const pag = document.getElementById('pagination');
  if (totalPages <= 1) {{ pag.innerHTML = `<span class="pag-info">${{filtered.length}} empresa(s)</span>`; return; }}

  let html = `<button class="pag-btn nav" onclick="goPage(${{page-1}})" ${{page===1?'disabled':''}}>&lsaquo;</button>`;
  for (let p = 1; p <= totalPages; p++) {{
    html += `<button class="pag-btn${{p===page?' active':''}}" onclick="goPage(${{p}})">${{p}}</button>`;
  }}
  html += `<button class="pag-btn nav" onclick="goPage(${{page+1}})" ${{page===totalPages?'disabled':''}}>&rsaquo;</button>`;
  html += `<span class="pag-info">${{filtered.length}} empresa(s) &nbsp;·&nbsp; página ${{page}} de ${{totalPages}}</span>`;
  pag.innerHTML = html;
}}

function goPage(p) {{ page = p; render(); }}

function clearFilters() {{
  document.getElementById('cap-min').value = '500000';
  Array.from(document.getElementById('setor-filter').options).forEach(o => o.selected = false);
  document.getElementById('search').value = '';
  page = 1;
  render();
}}

document.getElementById('cap-min').addEventListener('change', () => {{ page=1; render(); }});
document.getElementById('setor-filter').addEventListener('change', () => {{ page=1; render(); }});
document.getElementById('search').addEventListener('input', () => {{ page=1; render(); }});
render();
</script>
</body>
</html>"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_b4.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Preview gerado: {out}")
webbrowser.open(f"file:///{out}")
