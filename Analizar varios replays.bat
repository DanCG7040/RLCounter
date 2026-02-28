@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Seleccionar uno o varios .replay a la vez y generar JSON para cada uno

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"

set "LISTA="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.OpenFileDialog; $d.Filter = 'Replays (*.replay)|*.replay|Todos (*.*)|*.*'; $d.Title = 'Selecciona uno o varios replays (Ctrl o Shift para varios)'; $d.InitialDirectory = (Get-Location).Path; $d.Multiselect = $true; if ($d.ShowDialog() -eq 'OK') { $d.FileNames | ForEach-Object { Write-Output $_ } }"`) do (
  set "REPLAY=%%F"
  if exist "!REPLAY!" (
    set "OUT=%%~dpnF.json"
    echo Analizando: %%~nxF
    if not "%PY%"=="" ("%PY%" -m rl_replay_analyzer "!REPLAY!" -o "!OUT!" --indent 2) else (py -3.11 -m rl_replay_analyzer "!REPLAY!" -o "!OUT!" --indent 2)
    if errorlevel 1 (
      echo   ERROR en %%~nxF
    ) else (
      echo   OK -> %%~nF.json
    )
    echo.
    set "LISTA=!LISTA!x"
  )
)

if "%LISTA%"=="" (
  echo No se selecciono ningun archivo.
  pause
  exit /b 1
)

echo Listo. Revisa los JSON generados en la misma carpeta que cada replay.
pause
