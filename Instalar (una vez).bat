@echo off
cd /d "%~dp0"
setlocal

echo.
echo Creando/actualizando entorno virtual (.venv) y dependencias...
echo.

if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Error creando el venv. Asegurate de tener Python 3.11 instalado.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install -U pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
  echo.
  echo Error instalando dependencias.
  pause
  exit /b 1
)

echo.
echo OK. Ya puedes usar "Analizar Replay (doble clic).bat"
pause

