import duckdb, sys, json
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

ano_max = con.execute("SELECT MAX(ano) FROM fct_empregos").fetchone()[0]

# ── D1 ─────────────────────────────────────────────────────────────────────
df_d1 = con.execute(f"""
    SELECT e.id_municipio,
        SUM(e.total_vinculos * e.salario_medio_reais) / NULLIF(SUM(e.total_vinculos), 0) AS avg_sal,
        SUM(CASE WHEN e.salario_medio_sm >= 3 THEN e.total_vinculos ELSE 0 END) * 1.0
            / NULLIF(SUM(e.total_vinculos), 0) AS pct_3sm
    FROM fct_empregos e
    JOIN dim_municipio d ON d.id_municipio = e.id_municipio
    WHERE d.sigla_uf = 'SP' AND e.ano = {ano_max}
    GROUP BY 1
""").df()

# ── D2 ─────────────────────────────────────────────────────────────────────
df_d2 = con.execute(f"""
    WITH emp AS (
        SELECT id_municipio, SUM(total_vinculos) AS vinculos
        FROM fct_empregos WHERE ano = {ano_max} GROUP BY 1
    ),
    empres AS (
        SELECT id_municipio, COUNT(DISTINCT cnpj) AS n_grandes
        FROM fct_empresas WHERE porte = '5' AND capital_social >= 1000000 GROUP BY 1
    )
    SELECT d.id_municipio,
        COALESCE(v.vinculos, 0) AS vinculos,
        COALESCE(g.n_grandes, 0) * 1000.0 / NULLIF(COALESCE(v.vinculos, 0), 0) AS grandes_per_1k
    FROM dim_municipio d
    LEFT JOIN emp v ON v.id_municipio = d.id_municipio
    LEFT JOIN empres g ON g.id_municipio = d.id_municipio
    WHERE d.sigla_uf = 'SP'
""").df()

# ── D3 ─────────────────────────────────────────────────────────────────────
df_d3 = con.execute("""
    WITH conc AS (
        SELECT id_municipio,
            SUM(CASE WHEN nome_area_geral IN (
                'Negócios, administração e direito',
                'Tecnologias da informação e comunicação',
                'Engenharia, produção e construção'
            ) THEN total_concluintes ELSE 0 END) AS conc_alvo
        FROM fct_mercado_superior WHERE sigla_uf = 'SP' AND ano = 2024 GROUP BY 1
    )
    SELECT d.id_municipio,
        COALESCE(d.taxa_superior_25_mais, 0) AS taxa_superior,
        COALESCE(c.conc_alvo, 0) * 1000.0 / NULLIF(d.populacao_total, 0) AS conc_per_1k
    FROM dim_municipio d
    LEFT JOIN conc c ON c.id_municipio = d.id_municipio
    WHERE d.sigla_uf = 'SP'
""").df()

# ── D4 ─────────────────────────────────────────────────────────────────────
df_d4 = con.execute(f"""
    WITH v_atual AS (
        SELECT id_municipio, SUM(total_vinculos) AS v_atual FROM fct_empregos WHERE ano = {ano_max} GROUP BY 1
    ),
    v_2020 AS (
        SELECT id_municipio, SUM(total_vinculos) AS v_2020 FROM fct_empregos WHERE ano = 2020 GROUP BY 1
    )
    SELECT d.id_municipio, COALESCE(d.idhm, 0) AS idhm,
        CASE WHEN v0.v_2020 > 0 THEN (COALESCE(va.v_atual,0) - v0.v_2020)*1.0/v0.v_2020 ELSE NULL END AS cresc
    FROM dim_municipio d
    LEFT JOIN v_atual va ON va.id_municipio = d.id_municipio
    LEFT JOIN v_2020 v0 ON v0.id_municipio = d.id_municipio
    WHERE d.sigla_uf = 'SP'
""").df()

df_base = con.execute("""
    SELECT id_municipio, nome_municipio, populacao_total FROM dim_municipio WHERE sigla_uf='SP'
""").df()

con.close()

# ── Merge + normalize ───────────────────────────────────────────────────────
df = df_base.merge(df_d1, on="id_municipio", how="left") \
            .merge(df_d2, on="id_municipio", how="left") \
            .merge(df_d3, on="id_municipio", how="left") \
            .merge(df_d4, on="id_municipio", how="left")

cols_raw = ["avg_sal","pct_3sm","vinculos","grandes_per_1k","taxa_superior","conc_per_1k","idhm","cresc"]
df[cols_raw] = df[cols_raw].fillna(0)

def norm(s):
    mn, mx = s.min(), s.max()
    return (s - mn) / (mx - mn + 1e-10)

df["d1a"] = norm(df["avg_sal"])
df["d1b"] = norm(df["pct_3sm"])
df["d2a"] = norm(df["vinculos"])
df["d2b"] = norm(df["grandes_per_1k"])
df["d3a"] = norm(df["taxa_superior"])
df["d3b"] = norm(df["conc_per_1k"])
df["d4a"] = norm(df["idhm"])
df["d4b"] = norm(df["cresc"])

df["D1"] = ((df["d1a"] + df["d1b"]) / 2).round(4)
df["D2"] = ((df["d2a"] + df["d2b"]) / 2).round(4)
df["D3"] = ((df["d3a"] + df["d3b"]) / 2).round(4)
df["D4"] = ((df["d4a"] + df["d4b"]) / 2).round(4)

# ── JSON payload ─────────────────────────────────────────────────────────────
rows_json = json.dumps([
    {
        "id": r["id_municipio"],
        "nm": r["nome_municipio"],
        "pop": int(r["populacao_total"]) if r["populacao_total"] else 0,
        "D1": float(r["D1"]),
        "D2": float(r["D2"]),
        "D3": float(r["D3"]),
        "D4": float(r["D4"]),
        "sal": round(float(r["avg_sal"]), 0),
        "vinc": int(r["vinculos"]),
        "tsup": round(float(r["taxa_superior"]), 1),
        "idhm": round(float(r["idhm"]), 3),
        "cresc": round(float(r["cresc"]) * 100, 1)
    }
    for r in df.to_dict(orient="records")
], ensure_ascii=False)

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bloco 6 — Score de Atratividade | MVP Preview</title>
<script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
<style>
  :root {{
    --azul: #003087; --azul2: #0055A4; --verde: #00843D;
    --cinza-bg: #f5f6f8; --borda: #dde1e7;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--cinza-bg); color: #1a1a2e; }}
  header {{ background: var(--azul); color: #fff; padding: 14px 24px; display: flex; align-items: center; gap: 16px; }}
  header h1 {{ font-size: 1.1rem; font-weight: 600; }}
  header span {{ font-size: 0.8rem; opacity: 0.7; margin-left: auto; }}
  .badge {{ background: rgba(255,255,255,0.15); border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; }}
  .container {{ max-width: 1300px; margin: 0 auto; padding: 20px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 20px; }}
  .kpi {{ background: #fff; border-radius: 8px; padding: 14px 18px; border-left: 4px solid var(--azul2);
           box-shadow: 0 1px 4px rgba(0,0,0,.07); }}
  .kpi-label {{ font-size: .72rem; color: #666; text-transform: uppercase; letter-spacing: .04em; }}
  .kpi-value {{ font-size: 1.5rem; font-weight: 700; color: var(--azul); margin-top: 2px; }}
  .kpi-sub {{ font-size: .75rem; color: #888; margin-top: 2px; }}
  .card {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.07);
            padding: 18px 20px; margin-bottom: 16px; }}
  .card-title {{ font-size: .85rem; font-weight: 700; color: var(--azul); text-transform: uppercase;
                  letter-spacing: .06em; border-bottom: 2px solid var(--azul2); padding-bottom: 8px;
                  margin-bottom: 14px; }}
  .weights-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; }}
  .witem label {{ font-size: .8rem; color: #444; display: flex; justify-content: space-between; }}
  .witem input[type=range] {{ width: 100%; margin: 6px 0; accent-color: var(--azul2); }}
  .witem .wval {{ font-weight: 700; color: var(--azul); }}
  .w-total {{ text-align: right; font-size: .8rem; margin-top: 6px; }}
  .w-total.ok {{ color: var(--verde); }}
  .w-total.bad {{ color: #c0392b; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .search-bar {{ width: 100%; padding: 8px 12px; border: 1px solid var(--borda); border-radius: 6px;
                  font-size: .85rem; margin-bottom: 10px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .82rem; }}
  th {{ background: var(--azul); color: #fff; padding: 7px 10px; text-align: left; cursor: pointer;
         user-select: none; white-space: nowrap; }}
  th:hover {{ background: var(--azul2); }}
  tr:nth-child(even) {{ background: #f8f9fb; }}
  tr:hover {{ background: #e8edf7; cursor: pointer; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
  .score-bar {{ display: inline-block; height: 8px; border-radius: 4px; background: var(--azul2);
                vertical-align: middle; margin-right: 6px; }}
  .dim-pill {{ display: inline-block; padding: 1px 6px; border-radius: 10px; font-size: .7rem;
                font-weight: 600; }}
  .p1 {{ background: #dbeafe; color: #1d4ed8; }}
  .p2 {{ background: #dcfce7; color: #166534; }}
  .p3 {{ background: #fef3c7; color: #92400e; }}
  .p4 {{ background: #ede9fe; color: #5b21b6; }}
  .pagination {{ display: flex; gap: 6px; align-items: center; margin-top: 10px; flex-wrap: wrap; }}
  .pagination button {{ padding: 4px 10px; border: 1px solid var(--borda); border-radius: 4px;
                          background: #fff; cursor: pointer; font-size: .8rem; }}
  .pagination button.active {{ background: var(--azul); color: #fff; border-color: var(--azul); }}
  .pagination button:hover:not(.active) {{ background: #e8edf7; }}
  #radar-placeholder {{ color: #aaa; font-size: .85rem; text-align: center; padding: 60px 0; }}
  @media(max-width:900px) {{ .two-col, .weights-grid, .kpis {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <div>
    <div style="font-size:.7rem;opacity:.6;letter-spacing:.1em">PREVIEW — MVP</div>
    <h1>Bloco 6 &mdash; Score de Atratividade</h1>
  </div>
  <span class="badge">645 municípios SP · Pesos ajustáveis</span>
</header>

<div class="container">

  <!-- KPIs -->
  <div class="kpis" id="kpis">
    <div class="kpi">
      <div class="kpi-label">Municípios analisados</div>
      <div class="kpi-value">645</div>
      <div class="kpi-sub">São Paulo inteiro</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Maior score</div>
      <div class="kpi-value" id="kpi-top-score">—</div>
      <div class="kpi-sub" id="kpi-top-nm">—</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Campinas — rank</div>
      <div class="kpi-value" id="kpi-camp-rank">—</div>
      <div class="kpi-sub" id="kpi-camp-score">score: —</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Score médio SP</div>
      <div class="kpi-value" id="kpi-avg">—</div>
      <div class="kpi-sub">mediana: <span id="kpi-med">—</span></div>
    </div>
  </div>

  <!-- Pesos -->
  <div class="card">
    <div class="card-title">Ajuste de Pesos das Dimensões</div>
    <div class="weights-grid">
      <div class="witem">
        <label>D1 Capacidade de Pagamento <span class="wval" id="lw1">35%</span></label>
        <input type="range" id="w1" min="0" max="100" value="35" oninput="updateWeights()">
        <div style="font-size:.72rem;color:#666">Salário médio · % vínculos ≥3SM</div>
      </div>
      <div class="witem">
        <label>D2 Tamanho do Mercado <span class="wval" id="lw2">30%</span></label>
        <input type="range" id="w2" min="0" max="100" value="30" oninput="updateWeights()">
        <div style="font-size:.72rem;color:#666">Vínculos formais · Empresas grandes/1k</div>
      </div>
      <div class="witem">
        <label>D3 Pipeline Acadêmico <span class="wval" id="lw3">20%</span></label>
        <input type="range" id="w3" min="0" max="100" value="20" oninput="updateWeights()">
        <div style="font-size:.72rem;color:#666">Taxa sup. 25+ · Conc. alvo/1k hab</div>
      </div>
      <div class="witem">
        <label>D4 Dinamismo Econômico <span class="wval" id="lw4">15%</span></label>
        <input type="range" id="w4" min="0" max="100" value="15" oninput="updateWeights()">
        <div style="font-size:.72rem;color:#666">IDHM · Crescimento empregos 20→24</div>
      </div>
    </div>
    <div class="w-total ok" id="w-total">Total: 100% ✓</div>
  </div>

  <!-- Gráfico top + radar -->
  <div class="two-col">
    <div class="card">
      <div class="card-title">Top 20 Municípios</div>
      <div id="chart-top" style="height:340px"></div>
    </div>
    <div class="card">
      <div class="card-title">Perfil por Dimensão — <span id="radar-title" style="color:var(--azul2)">clique em uma linha</span></div>
      <div id="chart-radar" style="height:340px">
        <div id="radar-placeholder">Selecione um município na tabela abaixo para ver o perfil por dimensão</div>
      </div>
    </div>
  </div>

  <!-- Tabela -->
  <div class="card">
    <div class="card-title">Ranking Completo</div>
    <input class="search-bar" id="search" placeholder="Buscar município..." oninput="renderTable()">
    <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th onclick="sortBy('rank')">#</th>
            <th onclick="sortBy('nm')">Município</th>
            <th onclick="sortBy('score')">Score</th>
            <th onclick="sortBy('D1')">D1 Pagamento</th>
            <th onclick="sortBy('D2')">D2 Mercado</th>
            <th onclick="sortBy('D3')">D3 Pipeline</th>
            <th onclick="sortBy('D4')">D4 Dinamismo</th>
            <th onclick="sortBy('pop')">Popul.</th>
            <th onclick="sortBy('sal')">Sal. Médio</th>
            <th onclick="sortBy('idhm')">IDHM</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div class="pagination" id="pagination"></div>
  </div>

</div>

<script>
const RAW = {rows_json};

const PAGE = 20;
let page = 1, sortCol = 'rank', sortDir = 1;
let computed = [];

function getWeights() {{
  const w1 = +document.getElementById('w1').value;
  const w2 = +document.getElementById('w2').value;
  const w3 = +document.getElementById('w3').value;
  const w4 = +document.getElementById('w4').value;
  const tot = w1 + w2 + w3 + w4;
  return {{ w1, w2, w3, w4, tot }};
}}

function recompute() {{
  const {{w1,w2,w3,w4,tot}} = getWeights();
  const div = tot > 0 ? tot : 100;
  computed = RAW.map(r => ({{
    ...r,
    score: ((w1*r.D1 + w2*r.D2 + w3*r.D3 + w4*r.D4) / div * 100)
  }}));
  computed.sort((a,b) => b.score - a.score);
  computed.forEach((r,i) => r.rank = i+1);
}}

function updateWeights() {{
  const {{w1,w2,w3,w4,tot}} = getWeights();
  document.getElementById('lw1').textContent = w1 + '%';
  document.getElementById('lw2').textContent = w2 + '%';
  document.getElementById('lw3').textContent = w3 + '%';
  document.getElementById('lw4').textContent = w4 + '%';
  const el = document.getElementById('w-total');
  el.textContent = `Total: ${{tot}}% ${{tot===100?'✓':'⚠ (normalizado automaticamente)'}}`;
  el.className = 'w-total ' + (tot===100 ? 'ok' : 'bad');
  recompute();
  renderAll();
}}

function renderAll() {{
  updateKPIs();
  renderTopChart();
  renderTable();
}}

function updateKPIs() {{
  const avg = computed.reduce((s,r)=>s+r.score,0)/computed.length;
  const sorted = [...computed].sort((a,b)=>a.score-b.score);
  const med = sorted[Math.floor(sorted.length/2)].score;
  const top = computed[0];
  const camp = computed.find(r=>r.id==='3509502');
  document.getElementById('kpi-top-score').textContent = top.score.toFixed(1);
  document.getElementById('kpi-top-nm').textContent = top.nm;
  document.getElementById('kpi-camp-rank').textContent = '#' + camp.rank + '/645';
  document.getElementById('kpi-camp-score').textContent = 'score: ' + camp.score.toFixed(1);
  document.getElementById('kpi-avg').textContent = avg.toFixed(1);
  document.getElementById('kpi-med').textContent = med.toFixed(1);
}}

function renderTopChart() {{
  const top20 = computed.slice(0,20);
  const colors = top20.map(r => r.id === '3509502' ? '#00843D' : '#003087');
  Plotly.react('chart-top', [{{
    type: 'bar', orientation: 'h',
    x: top20.map(r=>r.score).reverse(),
    y: top20.map(r=>r.nm).reverse(),
    marker: {{ color: [...colors].reverse() }},
    text: top20.map(r=>r.score.toFixed(1)).reverse(),
    textposition: 'outside',
    hovertemplate: '%{{y}}<br>Score: %{{x:.1f}}<extra></extra>'
  }}], {{
    margin: {{l:140, r:40, t:10, b:30}},
    xaxis: {{range:[0, computed[0].score*1.15], title:'Score (0–100)'}},
    yaxis: {{tickfont:{{size:11}}}},
    paper_bgcolor:'white', plot_bgcolor:'white',
    height: 340, font: {{family:'Segoe UI'}}
  }}, {{displayModeBar:false}});
}}

function renderRadar(row) {{
  document.getElementById('radar-placeholder').style.display = 'none';
  document.getElementById('radar-title').textContent = row.nm;
  const dims = ['D1 Cap.Pagamento','D2 Tam.Mercado','D3 Pipeline','D4 Dinamismo'];
  const vals = [row.D1*100, row.D2*100, row.D3*100, row.D4*100];
  vals.push(vals[0]);
  const lbls = [...dims, dims[0]];
  Plotly.react('chart-radar', [{{
    type: 'scatterpolar', fill: 'toself',
    r: vals, theta: lbls,
    line: {{color:'#003087'}},
    fillcolor: 'rgba(0,48,135,0.15)',
    name: row.nm
  }}], {{
    polar: {{
      radialaxis: {{ visible: true, range: [0,100], tickfont:{{size:10}} }},
      angularaxis: {{ tickfont:{{size:11}} }}
    }},
    margin: {{l:50,r:50,t:20,b:20}},
    paper_bgcolor:'white', height:340, font:{{family:'Segoe UI'}},
    showlegend: false
  }}, {{displayModeBar:false}});
}}

function dimPill(val, cls) {{
  const pct = (val*100).toFixed(0);
  return `<span class="dim-pill ${{cls}}">${{pct}}</span>`;
}}

function renderTable() {{
  const q = document.getElementById('search').value.toLowerCase();
  let filtered = computed.filter(r => r.nm.toLowerCase().includes(q));
  filtered.sort((a,b) => {{
    const av = a[sortCol], bv = b[sortCol];
    if (typeof av === 'string') return sortDir * av.localeCompare(bv, 'pt');
    return sortDir * (av - bv);
  }});
  const total = filtered.length;
  const totalPages = Math.ceil(total / PAGE);
  if (page > totalPages) page = 1;
  const slice = filtered.slice((page-1)*PAGE, page*PAGE);

  const tbody = document.getElementById('tbody');
  tbody.innerHTML = slice.map(r => `
    <tr onclick="renderRadar(RAW.find(x=>x.id===\\'${{r.id}}\\'))">
      <td><b>${{r.rank}}</b></td>
      <td>${{r.nm}}</td>
      <td>
        <span class="score-bar" style="width:${{Math.round(r.score*1.5)}}px"></span>
        <b>${{r.score.toFixed(1)}}</b>
      </td>
      <td>${{dimPill(r.D1,'p1')}}</td>
      <td>${{dimPill(r.D2,'p2')}}</td>
      <td>${{dimPill(r.D3,'p3')}}</td>
      <td>${{dimPill(r.D4,'p4')}}</td>
      <td>${{r.pop > 0 ? (r.pop/1000).toFixed(0)+'k' : '-'}}</td>
      <td>R$ ${{r.sal > 0 ? r.sal.toLocaleString('pt-BR',{{maximumFractionDigits:0}}) : '-'}}</td>
      <td>${{r.idhm > 0 ? r.idhm.toFixed(3) : '-'}}</td>
    </tr>`).join('');

  // pagination
  const pag = document.getElementById('pagination');
  let html = '';
  const maxBtns = 7;
  let start = Math.max(1, page - Math.floor(maxBtns/2));
  let end = Math.min(totalPages, start + maxBtns - 1);
  if (end - start < maxBtns - 1) start = Math.max(1, end - maxBtns + 1);
  if (start > 1) html += `<button onclick="goPage(1)">1</button><span>…</span>`;
  for (let p = start; p <= end; p++)
    html += `<button class="${{p===page?'active':''}}" onclick="goPage(${{p}})">${{p}}</button>`;
  if (end < totalPages) html += `<span>…</span><button onclick="goPage(${{totalPages}})">${{totalPages}}</button>`;
  html += `<span style="margin-left:8px;font-size:.75rem;color:#888">${{total}} resultados</span>`;
  pag.innerHTML = html;
}}

function goPage(p) {{ page = p; renderTable(); }}
function sortBy(col) {{
  if (sortCol === col) sortDir *= -1; else {{ sortCol = col; sortDir = col==='nm' ? 1 : -1; }}
  renderTable();
}}

// Init
recompute();
renderAll();
// Pre-select Campinas
const camp = RAW.find(r=>r.id==='3509502');
if (camp) renderRadar(camp);
</script>
</body>
</html>"""

out = "data/preview_b6.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Preview salvo: {out}")
print(f"Municípios SP na payload: {len(df)}")
