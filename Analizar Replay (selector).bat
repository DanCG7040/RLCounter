@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Selector grafico de archivo (.replay) y analisis a JSON

REM Abrir cuadro de dialogo para elegir el replay
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command ^
  "Add-Type -AssemblyName System.Windows.Forms; ^
   $dlg = New-Object System.Windows.Forms.OpenFileDialog; ^
   $dlg.Filter = 'Replays (*.replay)|*.replay|Todos los archivos (*.*)|*.*'; ^
   $dlg.Title = 'Selecciona un replay de Rocket League'; ^
   $dlg.InitialDirectory = (Get-Location).Path; ^
   if ($dlg.ShowDialog() -eq 'OK') { Write-Output $dlg.FileName }"`) do (
  set "REPLAY=%%F"
)

if "%REPLAY%"=="" (
  echo No se selecciono ningun archivo.
  pause
  exit /b 1
)

if not exist "%REPLAY%" (
  echo No existe el archivo: "%REPLAY%"
  pause
  exit /b 1
)

REM Salida: mismo nombre que el replay, con extension .json
for %%F in ("%REPLAY%") do set "OUT=%%~dpnF.json"

REM Preferir venv si existe, si no usar py -3.11
set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"

if not "%PY%"=="" (
  "%PY%" -m rl_replay_analyzer "%REPLAY%" -o "%OUT%" --indent 2
) else (
  py -3.11 -m rl_replay_analyzer "%REPLAY%" -o "%OUT%" --indent 2
)

if errorlevel 1 (
  echo.
  echo Hubo un error analizando el replay.
  pause
  exit /b 1
)

echo.
echo OK. JSON generado en:
echo "%OUT%"
pause

