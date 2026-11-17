@echo off
chcp 65001 >nul
title Jarvis - Worker Windows
cd /d "%~dp0.."
if not exist "workstation_agent\.venv" (
  py -3 -m venv "workstation_agent\.venv"
  if errorlevel 1 goto erro
)
call "workstation_agent\.venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install requests
if not exist "workstation_agent\.env" (
  copy "workstation_agent\.env.example" "workstation_agent\.env" >nul
  echo Configure JARVIS_SERVER_URL, JARVIS_DEVICE_TOKEN e JARVIS_WORKSPACE no arquivo workstation_agent\.env
  notepad "workstation_agent\.env"
  pause
)
python -m workstation_agent.worker
pause
goto fim
:erro
echo Falha ao preparar Python. Instale Python 3.11+ com o launcher py.
pause
:fim
