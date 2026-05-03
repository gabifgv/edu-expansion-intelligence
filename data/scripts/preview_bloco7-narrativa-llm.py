import duckdb, sys, os, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# ── Parâmetros ────────────────────────────────────────────────────────────────
ID_MUN      = "3509502"
PRODUTO     = "MBA Executivo"
MENSALIDADE = 1200
RENDA_MIN   = 4000

con = duckdb.connect("data/sp_mvp.duckdb")
con.execute("SET enable_progress_bar=false")
ano_emp = con.execute("SELECT MAX(ano) FROM fct_empregos").fetchone()[0]

soc = con.execute(f"""
    SELECT nome_municipio, populacao_total, idhm, renda_per_capita,
           taxa_superior_25_mais, prop_pobreza
    FROM dim_municipio WHERE id_municipio = '{ID_MUN}'
""").fetchone()
nome_mun, pop, idhm, renda_pc, taxa_sup, pobreza = soc

emp = con.execute(f"""
    SELECT SUM(total_vinculos) vinculos,
           SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos ELSE 0 END) eleg,
           SUM(total_vinculos * salario_medio_reais) / NULLIF(SUM(total_vinculos),0) sal_medio,
           SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos*salario_medio_reais ELSE 0 END)
               / NULLIF(SUM(CASE WHEN salario_medio_reais >= {RENDA_MIN} THEN total_vinculos ELSE 0 END),0) sal_eleg
    FROM fct_empregos WHERE id_municipio = '{ID_MUN}' AND ano = {ano_emp}
""").fetchone()
vinculos, eleg, sal_medio, sal_eleg = emp

sup = con.execute(f"""
    SELECT SUM(CASE WHEN ano=2024 THEN total_concluintes ELSE 0 END) c24,
           SUM(CASE WHEN ano=2023 THEN total_concluintes ELSE 0 END) c23,
           COUNT(DISTINCT CASE WHEN ano=2024 THEN id_ies END) ies24
    FROM fct_mercado_superior WHERE id_municipio = '{ID_MUN}'
""").fetchone()
c24, c23, ies24 = sup

empresas_n = con.execute(f"""
    SELECT COUNT(DISTINCT cnpj) FROM fct_empresas
    WHERE id_municipio = '{ID_MUN}' AND porte = '5' AND capital_social >= 1000000
""").fetchone()[0]

con.close()

D1, D2, D3, D4 = 0.57, 0.12, 0.59, 0.48
score = (0.35*D1 + 0.30*D2 + 0.20*D3 + 0.15*D4) * 100
d23 = (c24-c23)/c23*100 if c23 else 0

# ── Contexto que será enviado ao Claude (para exibir no painel) ───────────────
contexto_display = f"""**Município:** {nome_mun} · **Produto:** {PRODUTO} · Mensalidade: R$ {MENSALIDADE:,}/mês

**Perfil:** Pop. {int(pop):,} · IDHM {idhm:.3f} · Renda p.c. R$ {renda_pc:,.0f} · Superior 25+: {taxa_sup:.1f}%

**Mercado ({ano_emp}):** {int(vinculos):,} vínculos formais · {int(eleg):,} elegíveis ({eleg/vinculos*100:.1f}%) · Sal. médio eleg. R$ {sal_eleg:,.0f}

**Empresas-alvo:** {int(empresas_n):,} empresas grandes (capital > R$1M)

**Pipeline:** {int(c24):,} concluintes 2024 · {int(ies24)} IES · vs 2023: {d23:+.1f}%

**Score:** {score:.1f}/100 (#4 SP) · D1 Pagamento: {D1*100:.0f} · D2 Mercado: {D2*100:.0f} · D3 Pipeline: {D3*100:.0f} · D4 Dinamismo: {D4*100:.0f}"""

# ── Narrativa: usa arquivo salvo pelo teste ou placeholder ────────────────────
narrativa_path = Path("data/narrativa_campinas.txt")
if narrativa_path.exists():
    narrativa_raw = narrativa_path.read_text(encoding="utf-8")
    tem_narrativa = True
else:
    narrativa_raw = ""
    tem_narrativa = False

def parse_paragrafos(texto):
    """Separa os 4 parágrafos pelo marcador **N. Título**"""
    import re
    partes = re.split(r'\*\*(\d+\.\s+[^\*]+)\*\*', texto.strip())
    result = []
    i = 1
    while i < len(partes) - 1:
        titulo = partes[i].strip()
        corpo = partes[i+1].strip() if i+1 < len(partes) else ""
        if titulo and corpo:
            result.append((titulo, corpo))
        i += 2
    return result

paragrafos = parse_paragrafos(narrativa_raw) if tem_narrativa else []

# ── HTML ──────────────────────────────────────────────────────────────────────
CORES_PARAG = ["#003087", "#0055A4", "#00843D", "#6B3FA0"]

cards_html = ""
if tem_narrativa and paragrafos:
    for i, (titulo, corpo) in enumerate(paragrafos):
        cor = CORES_PARAG[i % len(CORES_PARAG)]
        cards_html += f"""
        <div class="narrativa-card" style="border-left-color:{cor}">
          <div class="narrativa-titulo" style="color:{cor}">{titulo}</div>
          <div class="narrativa-corpo">{corpo}</div>
        </div>"""
else:
    cards_html = """
        <div id="placeholder-msg" style="text-align:center;padding:60px 20px;color:#aaa">
          <div style="font-size:2.5rem;margin-bottom:12px">⚡</div>
          <div style="font-size:1rem;font-weight:600;margin-bottom:8px">Análise não gerada ainda</div>
          <div style="font-size:.85rem">Clique em "Gerar análise" para acionar o Claude API com os dados deste município</div>
        </div>"""

contexto_json = json.dumps(contexto_display, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bloco 7 — Narrativa AI | MVP Preview</title>
<style>
  :root {{
    --azul: #003087; --azul2: #0055A4; --verde: #00843D;
    --cinza-bg: #f5f6f8; --borda: #dde1e7;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',system-ui,sans-serif; background:var(--cinza-bg); color:#1a1a2e; }}
  header {{ background:var(--azul); color:#fff; padding:14px 24px; display:flex; align-items:center; gap:16px; }}
  header h1 {{ font-size:1.1rem; font-weight:600; }}
  .badge {{ background:rgba(255,255,255,.15); border-radius:4px; padding:2px 8px; font-size:.75rem; margin-left:auto; }}
  .container {{ max-width:1100px; margin:0 auto; padding:20px; }}
  .card {{ background:#fff; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,.07); padding:18px 20px; margin-bottom:16px; }}
  .card-title {{ font-size:.85rem; font-weight:700; color:var(--azul); text-transform:uppercase;
                  letter-spacing:.06em; border-bottom:2px solid var(--azul2); padding-bottom:8px; margin-bottom:14px; }}
  .context-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:.83rem; line-height:1.7; }}
  .context-item strong {{ color:var(--azul); }}
  .btn-gerar {{ display:inline-flex; align-items:center; gap:8px; background:var(--azul);
                color:#fff; border:none; padding:10px 24px; border-radius:6px; font-size:.9rem;
                font-weight:600; cursor:pointer; transition:.15s; }}
  .btn-gerar:hover {{ background:var(--azul2); }}
  .btn-gerar:disabled {{ background:#aaa; cursor:not-allowed; }}
  .btn-copy {{ float:right; background:none; border:1px solid var(--borda); color:#666;
               padding:5px 12px; border-radius:4px; font-size:.75rem; cursor:pointer; }}
  .btn-copy:hover {{ background:#f0f0f0; }}
  .narrativa-card {{ border-left:4px solid var(--azul); padding:14px 18px; margin-bottom:14px;
                      background:#fafbfe; border-radius:0 6px 6px 0; }}
  .narrativa-titulo {{ font-size:.9rem; font-weight:700; margin-bottom:8px; }}
  .narrativa-corpo {{ font-size:.88rem; line-height:1.75; color:#2c2c3e; }}
  .loading {{ display:none; text-align:center; padding:40px; color:#888; }}
  .spinner {{ display:inline-block; width:24px; height:24px; border:3px solid #ddd;
               border-top-color:var(--azul); border-radius:50%; animation:spin .7s linear infinite; }}
  @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
  .tokens-info {{ font-size:.72rem; color:#aaa; text-align:right; margin-top:8px; }}
  .context-raw {{ font-family:monospace; font-size:.78rem; background:#f8f9fb;
                   border:1px solid var(--borda); border-radius:4px; padding:12px;
                   white-space:pre-wrap; line-height:1.6; color:#444; }}
  details summary {{ cursor:pointer; font-size:.8rem; color:var(--azul2); margin-bottom:8px; }}
  @media(max-width:700px) {{ .context-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <div>
    <div style="font-size:.7rem;opacity:.6;letter-spacing:.1em">PREVIEW — MVP</div>
    <h1>Bloco 7 &mdash; Narrativa Executiva AI</h1>
  </div>
  <span class="badge">Claude API · claude-opus-4-7</span>
</header>

<div class="container">

  <!-- Contexto enviado -->
  <div class="card">
    <div class="card-title">Dados Enviados ao Claude</div>
    <div style="font-size:.83rem;line-height:1.8;margin-bottom:14px">
      <strong>{nome_mun}</strong> &middot; {PRODUTO} &middot; Mensalidade R$ {MENSALIDADE:,}/mês
      &middot; Renda mínima R$ {RENDA_MIN:,}/mês &middot; Score {score:.1f}/100 (#4 SP)
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">
      <div style="background:#f0f4ff;border-radius:6px;padding:10px 12px">
        <div style="font-size:.7rem;color:#666;text-transform:uppercase">Vínculos elegíveis</div>
        <div style="font-size:1.2rem;font-weight:700;color:var(--azul)">{int(eleg):,}</div>
        <div style="font-size:.72rem;color:#888">{eleg/vinculos*100:.1f}% do total formal</div>
      </div>
      <div style="background:#f0fff4;border-radius:6px;padding:10px 12px">
        <div style="font-size:.7rem;color:#666;text-transform:uppercase">Sal. médio elegíveis</div>
        <div style="font-size:1.2rem;font-weight:700;color:var(--verde)">R$ {sal_eleg:,.0f}</div>
        <div style="font-size:.72rem;color:#888">vs R$ {RENDA_MIN:,} renda mínima</div>
      </div>
      <div style="background:#fff8f0;border-radius:6px;padding:10px 12px">
        <div style="font-size:.7rem;color:#666;text-transform:uppercase">Empresas grandes (&gt;1M)</div>
        <div style="font-size:1.2rem;font-weight:700;color:#d97706">{int(empresas_n):,}</div>
        <div style="font-size:.72rem;color:#888">na base CNPJ</div>
      </div>
    </div>
    <details>
      <summary>Ver contexto completo enviado ao Claude</summary>
      <div class="context-raw" id="ctx-raw">{contexto_display.replace('**','')}</div>
    </details>
  </div>

  <!-- Botão + narrativa -->
  <div class="card">
    <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
      <span>Análise Executiva</span>
      <div style="display:flex;gap:8px;align-items:center">
        {'<button class="btn-copy" onclick="copiarNarrativa()">⎘ Copiar texto</button>' if tem_narrativa else ''}
        <button class="btn-gerar" id="btn-gerar" onclick="gerarAnalise()">
          ⚡ {'Regenerar análise' if tem_narrativa else 'Gerar análise'}
        </button>
      </div>
    </div>

    <div class="loading" id="loading">
      <div class="spinner"></div>
      <div style="margin-top:12px;font-size:.85rem">Aguardando resposta do Claude...</div>
    </div>

    <div id="narrativa-area">
      {cards_html}
    </div>

    {'<div class="tokens-info" id="tokens-info"></div>' if not tem_narrativa else ''}
  </div>

  <!-- Nota metodológica -->
  <div class="card" style="font-size:.8rem;color:#666;line-height:1.7">
    <div class="card-title">Como funciona</div>
    <p>O Claude recebe um contexto estruturado com os KPIs dos blocos 1–6 (perfil socioeconômico,
    mercado de trabalho, empresas-alvo, pipeline universitário e score de atratividade) e gera
    4 parágrafos de análise executiva: dimensionamento do mercado, estratégia setorial,
    ações de prospecção e riscos/mitigações. O prompt força citação de números reais e
    recomendações acionáveis sem introduções genéricas.</p>
    <p style="margin-top:8px">No dashboard consolidado, o botão aciona <code>POST /api/analise-llm</code>
    com os parâmetros do município e produto selecionados. O modelo utilizado é
    <strong>claude-opus-4-7</strong> com ~1.200 tokens de saída.</p>
  </div>

</div>

<script>
const CONTEXTO = {contexto_json};

async function gerarAnalise() {{
  const btn = document.getElementById('btn-gerar');
  const loading = document.getElementById('loading');
  const area = document.getElementById('narrativa-area');
  btn.disabled = true;
  btn.textContent = '⏳ Gerando...';
  loading.style.display = 'block';
  area.innerHTML = '';
  try {{
    const resp = await fetch('/api/analise-llm', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        id_municipio: '{ID_MUN}',
        produto: '{PRODUTO}',
        mensalidade: {MENSALIDADE},
        renda_min: {RENDA_MIN}
      }})
    }});
    const data = await resp.json();
    renderNarrativa(data.narrativa);
    const ti = document.getElementById('tokens-info');
    if (ti && data.tokens) ti.textContent = `tokens: entrada ${{data.tokens.input}} · saída ${{data.tokens.output}}`;
  }} catch(e) {{
    area.innerHTML = `<div style="color:#c0392b;padding:20px">Erro: ${{e.message}}<br><small>Verifique se o servidor FastAPI está rodando e a chave ANTHROPIC_API_KEY está configurada.</small></div>`;
  }} finally {{
    loading.style.display = 'none';
    btn.disabled = false;
    btn.innerHTML = '⚡ Regenerar análise';
  }}
}}

const CORES = ['#003087','#0055A4','#00843D','#6B3FA0'];
function renderNarrativa(texto) {{
  const partes = texto.split(/\\*\\*(\\d+\\.\\s+[^\\*]+)\\*\\*/);
  const area = document.getElementById('narrativa-area');
  let html = '', idx = 0;
  for (let i = 1; i < partes.length - 1; i += 2) {{
    const cor = CORES[idx++ % CORES.length];
    html += `<div class="narrativa-card" style="border-left-color:${{cor}}">
      <div class="narrativa-titulo" style="color:${{cor}}">${{partes[i].trim()}}</div>
      <div class="narrativa-corpo">${{partes[i+1].trim()}}</div>
    </div>`;
  }}
  area.innerHTML = html || `<pre style="white-space:pre-wrap;font-size:.85rem">${{texto}}</pre>`;
}}

function copiarNarrativa() {{
  const texto = Array.from(document.querySelectorAll('.narrativa-titulo,.narrativa-corpo'))
    .map(el => el.textContent).join('\\n\\n');
  navigator.clipboard.writeText(texto);
  const btn = document.querySelector('.btn-copy');
  btn.textContent = '✓ Copiado!';
  setTimeout(() => btn.textContent = '⎘ Copiar texto', 2000);
}}
</script>
</body>
</html>"""

out = "data/preview_b7.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Preview salvo: {out}")
print(f"Narrativa pré-renderizada: {'SIM (data/narrativa_campinas.txt)' if tem_narrativa else 'NÃO (placeholder)'}")
