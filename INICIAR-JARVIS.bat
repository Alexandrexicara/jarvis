@echo off
cd /d "%~dp0Jarvis-Completo"
if exist "%~dp0..\workspace" (set "JARVIS_WORKSPACE=%~dp0..\workspace") else (set "JARVIS_WORKSPACE=%~dp0Jarvis-Completo")
python jarvis.py
pause
