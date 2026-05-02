import os
import math
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import queries as q

load_dotenv()

app = FastAPI(title="FGV Market Intelligence")
app.mount("/static", StaticFiles(directory="."), name="static")

geolocator = Nominatim(user_agent="fgv_inteligencia_mercado", timeout=10)
_cep_cache: dict[str, tuple[float, float]] = {}


# ─────────────────────────────────────────
# Serve o HTML principal
# ─────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse("index.html")


# ─────────────────────────────────────────
# Filtros — UFs e municípios
# ─────────────────────────────────────────

@app.get("/api/ufs")
def get_ufs():
    return q.get_ufs()


@app.get("/api/municipios/{sigla_uf}")
def get_municipios(sigla_uf: str):
    return q.get_municipios(sigla_uf)


# ─────────────────────────────────────────
# CEP → coordenadas (com cache em memória)
# ─────────────────────────────────────────

def geocode_cep(cep: str) -> tuple[float, float] | None:
    cep_clean = cep.replace("-", "").strip()
    if cep_clean in _cep_cache:
        return _cep_cache[cep_clean]
    try:
        loc = geolocator.geocode(f"{cep_clean}, Brasil")
        if loc:
            coords = (loc.latitude, loc.longitude)
            _cep_cache[cep_clean] = coords
            return coords
    except GeocoderTimedOut:
        pass
    return None


# ─────────────────────────────────────────
# Endpoint principal — carrega todos os blocos
# ─────────────────────────────────────────

class AnaliseRequest(BaseModel):
    id_municipio: str
    sigla_uf: str
    produto: str          # "MBA" ou "Pós-graduação"
    mensalidade: float
    percentual_renda: float = 9.0
    cep_polo: str | None = None


@app.post("/api/analise")
def analise(req: AnaliseRequest):
    renda_minima = req.mensalidade / (req.percentual_renda / 100)

    # Geocodifica o CEP do polo FGV (se fornecido)
    lat_polo, lon_polo = None, None
    if req.cep_polo:
        coords = geocode_cep(req.cep_polo)
        if coords:
            lat_polo, lon_polo = coords

    # Executa todos os blocos em paralelo via BQ
    try:
        perfil       = q.get_perfil_socioeconomico(req.id_municipio, req.sigla_uf)
        vinculos     = q.get_vinculos(req.id_municipio, req.sigla_uf, renda_minima)
        estab        = q.get_estabelecimentos(req.id_municipio, renda_minima)
        empresas     = q.get_empresas(req.id_municipio, renda_minima, lat_polo, lon_polo)
        formandos    = q.get_formandos(req.id_municipio)
        score        = q.get_score(req.id_municipio, req.sigla_uf, renda_minima)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "renda_minima": round(renda_minima, 2),
        "cep_polo_geocodificado": lat_polo is not None,
        "perfil": perfil,
        "vinculos": vinculos,
        "estabelecimentos": estab,
        "empresas": empresas,
        "formandos": formandos,
        "score": score,
    }


# ─────────────────────────────────────────
# Endpoint LLM — chamado separadamente
# ─────────────────────────────────────────

class LLMRequest(BaseModel):
    id_municipio: str
    sigla_uf: str
    produto: str
    mensalidade: float
    percentual_renda: float = 9.0
    # dados já carregados no frontend
    perfil: dict
    vinculos: dict
    estabelecimentos: dict
    formandos: dict
    score: dict


@app.post("/api/analise-llm")
def analise_llm(req: LLMRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY não configurada")

    prompt = q.get_llm_context(
        id_municipio=req.id_municipio,
        sigla_uf=req.sigla_uf,
        produto=req.produto,
        mensalidade=req.mensalidade,
        percentual_renda=req.percentual_renda,
        perfil=req.perfil,
        vinculos=req.vinculos,
        estabelecimentos=req.estabelecimentos,
        formandos=req.formandos,
        score=req.score,
    )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return {"narrativa": message.content[0].text}
