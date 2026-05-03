import duckdb, json, webbrowser, os, sys
sys.stdout.reconfigure(encoding='utf-8')

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")

id_municipio = "3509502"

# ── Carrega todos os dados de Campinas (filtros serão client-side) ─────────────
df = con.execute(f"""
    SELECT ano,
           nome_area_geral    AS area,
           nome_area_detalhada AS curso,
           nome_ies           AS ies,
           rede,
           modalidade_ensino  AS mod,
           COALESCE(total_concluintes, 0) AS conc
    FROM fct_mercado_superior
    WHERE id_municipio = '{id_municipio}'
""").df()
con.close()

# Serializa com chaves curtas para reduzir tamanho do JSON
rows_json = json.dumps([
    {"y": int(row["ano"]), "a": str(row["area"]), "c": str(row["curso"]),
     "i": str(row["ies"]), "r": str(row["rede"]), "m": str(row["mod"]), "n": float(row["conc"])}
    for row in df.to_dict(orient="records")
], ensure_ascii=False)

# Opções dos filtros
areas   = sorted(df["area"].dropna().unique().tolist())
ies_all = sorted(df["ies"].dropna().unique().tolist())

area_opts = '<option value="">Todas as áreas</option>' + "".join(
    f'<option value="{a}">{a}</option>' for a in areas)
ies_opts  = '<option value="">Todas as instituições</option>' + "".join(
    f'<option value="{i}">{i}</option>' for i in ies_all)

# Mapa area → cursos para cascata
area_cursos = {}
for a in areas:
    cursos = sorted(df[df["area"]==a]["curso"].dropna().unique().tolist())
    area_cursos[a] = cursos
area_cursos_json = json.dumps(area_cursos, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Bloco 5 — Pipeline Universitário</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:#0f172a; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:24px; }}
h2 {{ color:#38bdf8; margin-bottom:6px; font-size:1.3rem; }}
.meta {{ color:#94a3b8; font-size:.81rem; margin-bottom:18px; }}

/* Filtros */
.filters {{ display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px; align-items:flex-end; }}
.filters label {{ color:#94a3b8; font-size:.76rem; display:block; margin-bottom:3px; }}
select {{ background:#1e293b; border:1px solid #334155; color:#e2e8f0;
  border-radius:6px; padding:6px 10px; font-size:.81rem; outline:none; min-width:200px; }}
select:focus {{ border-color:#38bdf8; }}
.btn-clear {{ background:#334155; color:#94a3b8; border:none; border-radius:6px;
  padding:7px 14px; font-size:.8rem; cursor:pointer; }}
.btn-clear:hover {{ background:#475569; color:#e2e8f0; }}

/* KPIs */
.kpis {{ display:flex; gap:14px; margin-bottom:20px; flex-wrap:wrap; }}
.kpi {{ background:#1e293b; border:1px solid #334155; border-radius:10px;
  padding:14px 22px; min-width:160px; }}
.kpi .label {{ color:#94a3b8; font-size:.73rem; text-transform:uppercase; letter-spacing:.05em; }}
.kpi .value {{ color:#38bdf8; font-size:1.6rem; font-weight:700; margin-top:4px; }}
.kpi .delta {{ font-size:.82rem; margin-top:3px; }}
.pos {{ color:#34d399; }} .neg {{ color:#f87171; }} .neu {{ color:#94a3b8; }}

/* Gráficos */
.charts {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px; }}
.chart-card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:16px; }}
.chart-card h3 {{ color:#94a3b8; font-size:.78rem; text-transform:uppercase;
  letter-spacing:.05em; margin-bottom:10px; }}
.plotly-graph-div {{ width:100% !important; }}

/* Tabela */
.bottom {{ display:grid; grid-template-columns:2fr 1fr; gap:16px; }}
.card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:18px; }}
.card h3 {{ color:#94a3b8; font-size:.78rem; text-transform:uppercase;
  letter-spacing:.05em; margin-bottom:12px; }}
table {{ width:100%; border-collapse:collapse; font-size:.8rem; }}
thead th {{ color:#64748b; font-size:.7rem; text-transform:uppercase; letter-spacing:.05em;
  padding:7px 8px; text-align:left; border-bottom:1px solid #334155;
  cursor:pointer; user-select:none; white-space:nowrap; }}
thead th:hover {{ color:#e2e8f0; }}
thead th.r {{ text-align:right; }}
tbody tr {{ border-bottom:1px solid #1e2d3d; }}
tbody tr:hover {{ background:#243044; }}
td {{ padding:8px 8px; vertical-align:middle; }}
td.r {{ text-align:right; }}
.badge-area {{ display:inline-block; background:#0f2137; color:#7dd3fc;
  border-radius:3px; padding:1px 6px; font-size:.69rem; border:1px solid #1e4060; }}
.pos-sm {{ color:#34d399; font-size:.78rem; }}
.neg-sm {{ color:#f87171; font-size:.78rem; }}
.novo-sm {{ color:#fbbf24; font-size:.78rem; }}

/* Paginação */
.pag {{ display:flex; gap:5px; margin-top:12px; flex-wrap:wrap; align-items:center; }}
.pb {{ background:#1e293b; border:1px solid #334155; color:#94a3b8;
  border-radius:4px; padding:3px 9px; font-size:.77rem; cursor:pointer; }}
.pb:hover {{ border-color:#38bdf8; color:#e2e8f0; }}
.pb.on {{ background:#0ea5e9; border-color:#0ea5e9; color:#0f172a; font-weight:700; }}
.pag-info {{ color:#64748b; font-size:.75rem; margin-left:6px; }}

/* Cursos em Alta */
.alta-list {{ display:flex; flex-direction:column; gap:8px; }}
.alta-item {{ background:#0f172a; border:1px solid #1e3a5f; border-radius:8px; padding:10px 12px; }}
.alta-item .curso-nome {{ color:#e2e8f0; font-size:.82rem; font-weight:500; margin-bottom:4px; }}
.alta-item .area-tag {{ color:#64748b; font-size:.71rem; margin-bottom:6px; }}
.alta-metrics {{ display:flex; gap:14px; }}
.alta-metric .lbl {{ color:#64748b; font-size:.68rem; text-transform:uppercase; }}
.alta-metric .val {{ font-size:.85rem; font-weight:600; }}
.alta-rank {{ float:right; color:#fbbf24; font-weight:700; font-size:.85rem; }}
</style>
</head>
<body>

<h2>Bloco 5 — Pipeline Universitário</h2>
<p class="meta">Concluintes de graduação por área, curso e instituição · INEP · Campinas/SP</p>

<!-- Filtros globais -->
<div class="filters">
  <div>
    <label>Área geral</label>
    <select id="f-area" onchange="onAreaChange()">
      {area_opts}
    </select>
  </div>
  <div>
    <label>Curso / Área detalhada</label>
    <select id="f-curso">
      <option value="">Todos os cursos</option>
    </select>
  </div>
  <div>
    <label>Instituição</label>
    <select id="f-ies">
      {ies_opts}
    </select>
  </div>
  <div>
    <label>Modalidade</label>
    <select id="f-mod">
      <option value="">Todas</option>
      <option value="Presencial">Presencial</option>
      <option value="Curso a distância">EaD</option>
    </select>
  </div>
  <button class="btn-clear" onclick="clearFilters()">Limpar</button>
</div>

<!-- KPIs -->
<div class="kpis">
  <div class="kpi">
    <div class="label">Concluintes 2024</div>
    <div class="value" id="kpi-total">—</div>
    <div class="delta neu" id="kpi-ies">— IES</div>
  </div>
  <div class="kpi">
    <div class="label">Variação vs 2023</div>
    <div class="value" id="kpi-d23">—</div>
    <div class="delta neu" id="kpi-d23-abs">— concluintes</div>
  </div>
  <div class="kpi">
    <div class="label">Variação vs 2020</div>
    <div class="value" id="kpi-d20">—</div>
    <div class="delta neu" id="kpi-d20-abs">— concluintes</div>
  </div>
</div>

<!-- Gráficos -->
<div class="charts">
  <div class="chart-card">
    <h3>Concluintes por ano — Presencial vs EaD</h3>
    <div id="chart-serie"></div>
  </div>
  <div class="chart-card">
    <h3>Top 10 IES — Concluintes 2024</h3>
    <div id="chart-ies"></div>
  </div>
</div>

<!-- Tabela + Cursos em Alta -->
<div class="bottom">
  <div class="card">
    <h3>Área · Curso · Concluintes</h3>
    <table>
      <thead>
        <tr>
          <th onclick="sortTable('area')">Área <span id="arr-area"></span></th>
          <th onclick="sortTable('curso')">Curso <span id="arr-curso"></span></th>
          <th class="r" onclick="sortTable('c2024')">2024 <span id="arr-c2024"></span></th>
          <th class="r" onclick="sortTable('pct')">% <span id="arr-pct"></span></th>
          <th class="r" onclick="sortTable('delta')">Δ 2023 <span id="arr-delta"></span></th>
        </tr>
      </thead>
      <tbody id="table-body"></tbody>
    </table>
    <div class="pag" id="pag"></div>
  </div>
  <div class="card">
    <h3>🚀 Cursos em Alta</h3>
    <p style="color:#64748b;font-size:.73rem;margin-bottom:10px">
      Cursos com ≥ 100 concluintes em 2024 e crescimento positivo desde 2020.<br>
      Score = share × crescimento.
    </p>
    <div class="alta-list" id="alta-list"></div>
  </div>
</div>

<script>
const ALL = {rows_json};
const AREA_CURSOS = {area_cursos_json};
const ANOS = [2020,2021,2022,2023,2024];
const PLT = {{ responsive:true }};
const DARK = {{ paper_bgcolor:'transparent', plot_bgcolor:'transparent',
  font:{{color:'#94a3b8', size:11}},
  margin:{{t:10,b:40,l:10,r:10}},
  xaxis:{{gridcolor:'#1e2d3d', linecolor:'#334155'}},
  yaxis:{{gridcolor:'#1e2d3d', linecolor:'#334155'}} }};

let tblSort = 'c2024', tblDir = -1, tblPage = 1;
const TBL_PAGE = 15;

function getFiltered() {{
  const a = document.getElementById('f-area').value;
  const c = document.getElementById('f-curso').value;
  const i = document.getElementById('f-ies').value;
  const m = document.getElementById('f-mod').value;
  return ALL.filter(r =>
    (!a || r.a === a) &&
    (!c || r.c === c) &&
    (!i || r.i === i) &&
    (!m || r.m === m)
  );
}}

function sum(arr, key) {{ return arr.reduce((s,r) => s + (r[key]||0), 0); }}

function pct(a, b) {{
  if (!b) return null;
  return (a - b) / b * 100;
}}

function fmtPct(v, cls=true) {{
  if (v === null || v === undefined || !isFinite(v)) return '<span class="novo-sm">novo</span>';
  const s = (v>=0?'+':'')+v.toFixed(1)+'%';
  if (!cls) return s;
  return `<span class="${{v>=0?'pos-sm':'neg-sm'}}">${{s}}</span>`;
}}

function renderKPIs(rows) {{
  const c24 = sum(rows.filter(r=>r.y===2024), 'n');
  const c23 = sum(rows.filter(r=>r.y===2023), 'n');
  const c20 = sum(rows.filter(r=>r.y===2020), 'n');
  const ies24 = new Set(rows.filter(r=>r.y===2024).map(r=>r.i)).size;
  const d23 = pct(c24,c23), d20 = pct(c24,c20);

  document.getElementById('kpi-total').textContent = c24.toLocaleString('pt-BR');
  document.getElementById('kpi-ies').textContent = `${{ies24}} IES`;
  const el23 = document.getElementById('kpi-d23');
  el23.textContent = d23!==null ? (d23>=0?'+':'')+d23.toFixed(1)+'%' : '—';
  el23.className = 'value ' + (d23===null?'neu':d23>=0?'pos':'neg');
  document.getElementById('kpi-d23-abs').textContent = d23!==null ? `${{(c24-c23>=0?'+':'')+(c24-c23).toLocaleString('pt-BR')}} concluintes` : '';
  const el20 = document.getElementById('kpi-d20');
  el20.textContent = d20!==null ? (d20>=0?'+':'')+d20.toFixed(1)+'%' : '—';
  el20.className = 'value ' + (d20===null?'neu':d20>=0?'pos':'neg');
  document.getElementById('kpi-d20-abs').textContent = d20!==null ? `${{(c24-c20>=0?'+':'')+(c24-c20).toLocaleString('pt-BR')}} concluintes` : '';
}}

function renderSerie(rows) {{
  const pres = ANOS.map(y => sum(rows.filter(r=>r.y===y&&r.m==='Presencial'),'n'));
  const ead  = ANOS.map(y => sum(rows.filter(r=>r.y===y&&r.m==='Curso a distância'),'n'));
  Plotly.react('chart-serie', [
    {{ x:ANOS, y:pres, name:'Presencial', type:'bar', marker:{{color:'#0ea5e9'}} }},
    {{ x:ANOS, y:ead,  name:'EaD',        type:'bar', marker:{{color:'#6366f1'}} }}
  ], {{ ...DARK, barmode:'stack', legend:{{orientation:'h',y:1.08}},
    yaxis:{{...DARK.yaxis, title:''}} }}, PLT);
}}

function renderIES(rows) {{
  const byIES = {{}};
  rows.filter(r=>r.y===2024).forEach(r => {{ byIES[r.i] = (byIES[r.i]||0)+r.n; }});
  const sorted = Object.entries(byIES).sort((a,b)=>b[1]-a[1]).slice(0,10);
  const names = sorted.map(([k])=>k.length>30?k.slice(0,28)+'…':k).reverse();
  const vals  = sorted.map(([,v])=>v).reverse();
  const colors = sorted.map(([k])=> {{
    const rede = (rows.find(r=>r.i===k)||{{}}).r;
    return rede==='Pública' ? '#34d399' : '#0ea5e9';
  }}).reverse();
  Plotly.react('chart-ies', [
    {{ y:names, x:vals, type:'bar', orientation:'h',
       marker:{{color:colors}},
       text:vals.map(v=>v.toLocaleString('pt-BR')), textposition:'outside',
       cliponaxis:false }}
  ], {{ ...DARK, showlegend:false,
    xaxis:{{...DARK.xaxis, title:''}},
    yaxis:{{...DARK.yaxis, automargin:true}},
    margin:{{t:10,b:30,l:10,r:60}} }}, PLT);
}}

function buildAreaBaseline(rows, yearNew, yearOld) {{
  // For each area: sum concluintes in yearOld for courses that vanished by yearNew
  const by = {{}};
  rows.filter(r=>r.y===yearNew||r.y===yearOld).forEach(r=>{{
    const k=r.a+'|||'+r.c;
    if(!by[k]) by[k]={{area:r.a, cNew:0, cOld:0}};
    if(r.y===yearNew) by[k].cNew+=r.n; else by[k].cOld+=r.n;
  }});
  const base={{}};
  Object.values(by).forEach(r=>{{
    if(r.cNew===0 && r.cOld>0) base[r.area]=(base[r.area]||0)+r.cOld;
  }});
  return base;
}}

function renderTable(rows) {{
  const total24 = sum(rows.filter(r=>r.y===2024),'n');
  const areaBase23 = buildAreaBaseline(rows, 2024, 2023);
  const by = {{}};
  rows.filter(r=>r.y===2024||r.y===2023).forEach(r=>{{
    const k = r.a+'|||'+r.c;
    if(!by[k]) by[k]={{area:r.a, curso:r.c, c2024:0, c2023:0}};
    if(r.y===2024) by[k].c2024+=r.n; else by[k].c2023+=r.n;
  }});
  let rows2 = Object.values(by).filter(r=>r.c2024>0).map(r=>{{
    const baseline = r.c2023>0 ? r.c2023 : (areaBase23[r.area]||0);
    const delta = baseline>0 ? pct(r.c2024, baseline) : null;
    const isReclass = r.c2023===0 && (areaBase23[r.area]||0)>0;
    return {{...r, pct: total24>0?r.c2024/total24*100:0, delta, isReclass}};
  }});

  rows2.sort((a,b) => {{
    const va=a[tblSort], vb=b[tblSort];
    if(va===null&&vb===null) return 0;
    if(va===null) return 1; if(vb===null) return -1;
    return tblDir*(typeof va==='string'?va.localeCompare(vb,'pt'):(va-vb));
  }});

  ['area','curso','c2024','pct','delta'].forEach(c=>{{
    const el=document.getElementById('arr-'+c);
    if(el) el.textContent = tblSort===c?(tblDir===-1?'▼':'▲'):'';
  }});

  const total = rows2.length;
  const totalPages = Math.max(1, Math.ceil(total/TBL_PAGE));
  tblPage = Math.min(tblPage, totalPages);
  const slice = rows2.slice((tblPage-1)*TBL_PAGE, tblPage*TBL_PAGE);
  const offset = (tblPage-1)*TBL_PAGE;

  document.getElementById('table-body').innerHTML = slice.map((r,i)=>`
    <tr>
      <td><span class="badge-area">${{r.area.length>28?r.area.slice(0,26)+'…':r.area}}</span></td>
      <td>${{r.curso}}${{r.isReclass?' <span title="INEP reclassificou em 2024 — delta vs soma predecessoras" style="color:#fbbf24;font-size:.68rem;cursor:help">⚠ reclass.</span>':''}}</td>
      <td class="r" style="font-weight:500">${{r.c2024.toLocaleString('pt-BR')}}</td>
      <td class="r" style="color:#94a3b8">${{r.pct.toFixed(1)}}%</td>
      <td class="r">${{fmtPct(r.delta)}}</td>
    </tr>`).join('');

  // paginação
  const pag = document.getElementById('pag');
  if(totalPages<=1){{ pag.innerHTML=`<span class="pag-info">${{total}} cursos</span>`; return; }}
  let h = `<button class="pb" onclick="goTbl(${{tblPage-1}})" ${{tblPage===1?'disabled':''}}>&lsaquo;</button>`;
  for(let p=1;p<=totalPages;p++) h+=`<button class="pb${{p===tblPage?' on':''}}" onclick="goTbl(${{p}})">${{p}}</button>`;
  h+=`<button class="pb" onclick="goTbl(${{tblPage+1}})" ${{tblPage===totalPages?'disabled':''}}>&rsaquo;</button>`;
  h+=`<span class="pag-info">${{total}} cursos · pág ${{tblPage}}/${{totalPages}}</span>`;
  pag.innerHTML = h;
}}

function renderAlta(rows) {{
  const total24 = sum(rows.filter(r=>r.y===2024),'n');
  const areaBase20 = buildAreaBaseline(rows, 2024, 2020);
  const by = {{}};
  rows.filter(r=>r.y===2024||r.y===2020).forEach(r=>{{
    const k = r.a+'|||'+r.c;
    if(!by[k]) by[k]={{area:r.a, curso:r.c, c2024:0, c2020:0}};
    if(r.y===2024) by[k].c2024+=r.n; else by[k].c2020+=r.n;
  }});
  const alta = Object.values(by)
    .filter(x=>x.c2024>=100)
    .map(x=>{{
      const base20 = x.c2020>0 ? x.c2020 : (areaBase20[x.area]||0);
      if(!base20 || x.c2024<=base20) return null;
      const cresc=(x.c2024-base20)/base20;
      const share=total24>0?x.c2024/total24:0;
      const isReclass = x.c2020===0 && (areaBase20[x.area]||0)>0;
      return {{...x, base20, cresc:cresc*100, share:share*100, score:share*cresc, isReclass}};
    }}).filter(Boolean)
    .sort((a,b)=>b.score-a.score).slice(0,7);

  document.getElementById('alta-list').innerHTML = alta.map((x,i)=>`
    <div class="alta-item">
      <div class="alta-rank">#${{i+1}}</div>
      <div class="curso-nome">${{x.curso}}</div>
      <div class="area-tag">${{x.area}}</div>
      <div class="alta-metrics">
        <div class="alta-metric">
          <div class="lbl">Concluintes 24</div>
          <div class="val" style="color:#38bdf8">${{x.c2024.toLocaleString('pt-BR')}}</div>
        </div>
        <div class="alta-metric">
          <div class="lbl">Share</div>
          <div class="val" style="color:#a78bfa">${{x.share.toFixed(1)}}%</div>
        </div>
        <div class="alta-metric">
          <div class="lbl">Cresc 20→24</div>
          <div class="val" style="color:#34d399">+${{x.cresc.toFixed(0)}}%</div>
        </div>
      </div>
      ${{x.isReclass?'<div style="color:#fbbf24;font-size:.68rem;margin-top:4px">⚠ INEP reclassificou em 2024</div>':''}}
    </div>`).join('');
}}

function render() {{
  const rows = getFiltered();
  renderKPIs(rows);
  renderSerie(rows);
  renderIES(rows);
  renderTable(rows);
  renderAlta(rows);
}}

function sortTable(col) {{
  if(tblSort===col) tblDir*=-1; else {{tblSort=col; tblDir=-1;}}
  tblPage=1; render();
}}
function goTbl(p) {{ tblPage=p; render(); }}

function onAreaChange() {{
  const a = document.getElementById('f-area').value;
  const sel = document.getElementById('f-curso');
  sel.innerHTML = '<option value="">Todos os cursos</option>';
  if(a && AREA_CURSOS[a]) {{
    AREA_CURSOS[a].forEach(c => {{
      const o = document.createElement('option');
      o.value = c; o.textContent = c; sel.appendChild(o);
    }});
  }}
  tblPage=1; render();
}}

function clearFilters() {{
  ['f-area','f-curso','f-ies','f-mod'].forEach(id => {{
    document.getElementById(id).value='';
  }});
  document.getElementById('f-curso').innerHTML='<option value="">Todos os cursos</option>';
  tblPage=1; render();
}}

['f-curso','f-ies','f-mod'].forEach(id =>
  document.getElementById(id).addEventListener('change', ()=>{{ tblPage=1; render(); }})
);

render();
</script>
</body>
</html>"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_b5.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Preview gerado: {out}")
webbrowser.open(f"file:///{out}")
