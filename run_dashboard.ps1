#!/usr/bin/env pwsh

# Ativa o venv do dashboard
.\dashboard_venv\Scripts\Activate.ps1

# Vai para a pasta dashboard
cd dashboard

# Verifica .env
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env não encontrado. Criando com placeholder..."
    @"
ANTHROPIC_API_KEY=sk-ant-...
"@ | Out-File -Encoding UTF8 ".env"
    Write-Host "⚠️  Edite .env com sua chave real da API Anthropic"
}

# Roda o uvicorn
Write-Host "🚀 Iniciando dashboard em http://localhost:8000"
uvicorn app:app --reload --host 0.0.0.0 --port 8000
