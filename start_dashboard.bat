@echo off
echo Iniciando dashboard DICOM MARKET...

:: Mata processo existente na porta 8001, se houver
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Inicia o servidor
cd /d "%~dp0dashboard"
start "" /B "..\\.venv\\Scripts\\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8001

:: Aguarda subir
timeout /t 2 /nobreak >nul

echo Servidor rodando em http://127.0.0.1:8001
start http://127.0.0.1:8001
