@echo off
cd /d "%~dp0"
pythonw "%~dp0Analizar_Replay.pyw"
if errorlevel 1 (
    python "%~dp0Analizar_Replay.pyw"
    pause
)
