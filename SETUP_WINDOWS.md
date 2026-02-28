# Configuración en Windows (Python 3.11 + boxcars-py)

## 1. Python 3.11 (64-bit)

- Descarga: https://www.python.org/downloads/release/python-3110/
- En el instalador, marca **"Add Python to PATH"**.
- Comprueba: `py -3.11 --version` → `Python 3.11.x`

## 2. Entorno virtual

```powershell
cd c:\Users\danie\Escritorio\Rl\Contador
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version   # debe ser 3.11.x
```

## 3. Rust (toolchain estable)

- Instalar: https://rustup.rs/ (en Windows usa el .exe).
- En una terminal **nueva** (para que cargue el PATH):

```powershell
rustup default stable
rustc --version
cargo --version
```

## 4. Compilar boxcars-py en Windows: enlazador MSVC

El error `link.exe not found` significa que falta el **enlazador de C++ de Microsoft**.

### Opción recomendada: Build Tools para Visual Studio

1. Descarga **Build Tools for Visual Studio**:  
   https://visualstudio.microsoft.com/es/visual-cpp-build-tools/
2. En el instalador elige la carga **"Desarrollo para el escritorio con C++"** (Desktop development with C++).
3. Asegúrate de que esté marcado **MSVC** y **Windows SDK**.
4. Instala, reinicia la terminal y:

```powershell
cd c:\Users\danie\Escritorio\Rl\Contador
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 5. Comprobar que todo funciona

```powershell
python -m rl_replay_analyzer archivo.replay -o resultado.json --indent 2
type resultado.json
```

Si ves un JSON con `teams` y `goals`, el proyecto está funcionando. Los tiempos se obtienen del stream de red (evento GoalScored + SecondsRemaining).

## Nota importante (replays recientes)

Para replays recientes, se recomienda el fork mantenido **`sprocket-boxcars-py`** (incluido en `requirements.txt`), que soporta más versiones de replay en Windows.
