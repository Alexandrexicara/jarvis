@echo off
chcp 65001 >nul
title Jarvis - Worker Windows
cd /d "%~dp0"
if not exist ".venv" (
  py -3 -m venv .venv
  if errorlevel 1 goto erro
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install requests
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Configure JARVIS_SERVER_URL, JARVIS_DEVICE_TOKEN e JARVIS_WORKSPACE no arquivo .env
  notepad ".env"
  pause
)
python -c "from pathlib import Path; p=Path('.env'); d={}; [d.update([line.split('=',1)]) for line in p.read_text(encoding='utf-8').splitlines() if '=' in line and not line.lstrip().startswith('#')]; import os; os.environ.update(d)"
python -m workstation_agent.worker
pause
goto fim
:erro
echo Falha ao preparar Python. Instale Python 3.11+ com o launcher py.
pause
:fim
