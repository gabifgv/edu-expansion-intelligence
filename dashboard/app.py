"""
FGV Market Intelligence Platform — FastAPI backend
Serve o dashboard consolidado e expõe os endpoints dos 7 blocos.
Lê de DuckDB local (data/sp_mvp.duckdb).
"""
import os
import urllib.request
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import queries_duckdb as q

load_dotenv()

app = FastAPI(title="FGV Market Intelligence")

DASHBOARD_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")

# ── Cache em memória de geocodificação ────────────────────────────────────────
_cep_cache: dict = {}


def geocodificar_cep(cep: str) -> Optional[tuple]:
    """Retorna (lat, lon) via BrasilAPI ou DuckDB. Cacheia em memória."""
    cep = cep.replace("-", "").replace(".", "").strip()
    if not cep or len(cep) < 8:
        return None
    if cep in _cep_cache:
        return _cep_cache[cep]

    # Tenta BrasilAPI
    try:
        req = urllib.request.Request(
            f"https://brasilapi.com.br/api/cep/v2/{cep}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read())
        coords = d.get("location", {}).get("coordinates", {})
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        if lat and lon:
            _cep_cache[cep] = (float(lat), float(lon))
            return _cep_cache[cep]
    except Exception:
        pass

    # Fallback: dim_cep_coords no DuckDB
    try:
        con = q.get_con()
        row = con.execute(f"SELECT latitude, longitude FROM dim_cep_coords WHERE cep = '{cep}'").fetchone()
        con.close()
        if row and row[0] and row[1]:
            _cep_cache[cep] = (float(row[0]), float(row[1]))
            return _cep_cache[cep]
    except Exception:
        pass

    return None


# ── Página principal ──────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(str(DASHBOARD_DIR / "index.html"))


# ── Filtros: UFs e municípios ─────────────────────────────────────────────────
@app.get("/api/ufs")
def get_ufs():
    return q.list_ufs()


@app.get("/api/municipios/{sigla_uf}")
def get_municipios(sigla_uf: str):
    return q.list_municipios(sigla_uf)


# ── Análise principal: blocos 1-6 em uma chamada ─────────────────────────────
class AnaliseRequest(BaseModel):
    id_municipio: str
    sigla_uf: str
    produto: str = "MBA Executivo"
    mensalidade: float = 1200
    pct_renda: float = 30
    cep_polo: Optional[str] = None
    capital_min: float = 500_000


@app.post("/api/analise")
def analise(req: AnaliseRequest):
    renda_min = req.mensalidade / (req.pct_renda / 100)

    # Geocodifica CEP da gestora (opcional)
    lat_polo, lon_polo = None, None
    if req.cep_polo:
        coords = geocodificar_cep(req.cep_polo)
        if coords:
            lat_polo, lon_polo = coords

    con = q.get_con()
    try:
        ano_emp = con.execute("SELECT MAX(ano) FROM fct_empregos").fetchone()[0]

        perfil = q.get_perfil(con, req.id_municipio, req.sigla_uf, renda_min, ano_emp)
        mt = q.get_mercado_trabalho(con, req.id_municipio, renda_min, ano_emp)
        empresas = q.get_empresas(
            con, req.id_municipio,
            capital_min=req.capital_min,
            lat_polo=lat_polo, lon_polo=lon_polo,
        )
        pipeline = q.get_pipeline(con, req.id_municipio)
        score = q.get_score_estado(con, req.sigla_uf, ano_emp)
    finally:
        con.close()

    payload = {
        "renda_min": round(renda_min, 0),
        "ano_emp": ano_emp,
        "cep_geocodificado": lat_polo is not None,
        "perfil": perfil,
        "mercado_trabalho": mt,
        "empresas": empresas,
        "pipeline": pipeline,
        "score": score,
    }
    return q._clean_nan(payload)


# ── Bloco 7: narrativa LLM ────────────────────────────────────────────────────
class LLMRequest(BaseModel):
    id_municipio: str
    sigla_uf: str
    produto: str = "MBA Executivo"
    mensalidade: float = 1200
    pct_renda: float = 30
    perfil: dict
    mercado_trabalho: dict
    empresas: dict
    pipeline: dict
    score: dict


@app.post("/api/analise-llm")
def analise_llm(req: LLMRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.startswith("sk-ant-v0-placeholder"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY não configurada em dashboard/.env")

    con = q.get_con()
    try:
        result = q.get_narrativa_llm(
            con,
            id_municipio=req.id_municipio,
            sigla_uf=req.sigla_uf,
            produto=req.produto,
            mensalidade=req.mensalidade,
            pct_renda=req.pct_renda,
            perfil_data=req.perfil,
            mt_data=req.mercado_trabalho,
            empresas_data=req.empresas,
            pipeline_data=req.pipeline,
            score_data=req.score,
            api_key=api_key,
        )
    finally:
        con.close()

    return result
