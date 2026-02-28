# Analizador de replays de Rocket League (Contador)

Este proyecto es un **programa en Python** que lee archivos de partida guardados de **Rocket League** (archivos `.replay`) y extrae de ellos:

- Los **nombres de los equipos** (azul y naranja), sobre todo en partidas privadas donde pones nombres personalizados.
- La **lista de goles** en orden: a qué minuto se marcó cada gol y qué equipo lo hizo.

El resultado se guarda en un archivo **JSON** que luego puedes usar en una web, base de datos, etc.

**No hace falta saber programar:** puedes usar el programa haciendo doble clic en un archivo y eligiendo el replay. El resto de este README explica **cómo está hecho el código por dentro**, por si quieres entenderlo o modificarlo.

---

## Requisitos

- **Python 3.10 o superior** instalado en el ordenador.
- No hace falta instalar Rust ni compilar nada: el programa incluye un lector del archivo `.replay` escrito solo en Python.

---

## Instalación rápida

Abre una terminal (PowerShell o CMD) en la carpeta del proyecto y ejecuta:

```bash
cd Contador
pip install -r requirements.txt
```

Con eso se instalan las dependencias (por ahora el proyecto casi no usa librerías externas; el lector del replay es propio).

---

## Cómo usar el programa (sin tocar código)

### Opción 1: Con doble clic (la más fácil)

1. Tener un archivo `.replay` de Rocket League (por ejemplo en `Documentos\My Games\Rocket League\TAGame\Demos`).
2. Haz **doble clic** en:
   - **`Analizar_Replay.pyw`**, o
   - **`Analizar Replay (doble clic).bat`**
3. Se abrirá una ventana para elegir archivo. Elige tu `.replay`.
4. El programa creará un archivo **`resultado.json`** en la **misma carpeta donde está el replay** y te mostrará un mensaje con los equipos y el número de goles. También abrirá esa carpeta.

No hace falta escribir nada en la consola.

### Opción 2: Desde la consola

```bash
python -m rl_replay_analyzer partida.replay
```

Esto genera `resultado.json` en la carpeta actual. Para guardar en otra ruta:

```bash
python -m rl_replay_analyzer partida.replay -o C:\ruta\resultado.json
```

---

## Qué contiene el archivo resultado.json

El JSON tiene esta forma:

```json
{
  "teams": {
    "blue": "NombreEquipoAzul",
    "orange": "NombreEquipoNaranja"
  },
  "goals": [
    { "time": "04:23", "team": "NombreEquipoAzul" },
    { "time": "02:11", "team": "NombreEquipoNaranja" }
  ]
}
```

- **teams**: nombres del equipo azul y del naranja (en partidas privadas son los que pusiste en el lobby).
- **goals**: lista de goles en orden; cada uno tiene **time** (minuto:segundo) y **team** (nombre del equipo que anotó).

---

# Explicación del código (archivo por archivo y función por función)

A partir de aquí se explica **cada archivo y cada función** como si no supieras nada de Python. Puedes usarlo como guía para leer el código.

---

## Resumen de archivos del proyecto

| Archivo | Qué hace en una frase |
|--------|------------------------|
| `Analizar_Replay.pyw` | Programa con ventana: al hacer doble clic pide un `.replay`, lo analiza y guarda `resultado.json`. |
| `Analizar Replay (doble clic).bat` | Script de Windows que ejecuta `Analizar_Replay.pyw` sin abrir consola. |
| `requirements.txt` | Lista de dependencias de Python (por ahora casi vacía). |
| `ejemplo_resultado.json` | Ejemplo del JSON que genera el programa. |
| `rl_replay_analyzer/` | Carpeta del “módulo” principal: aquí está toda la lógica de leer el replay y extraer equipos y goles. |

Dentro de `rl_replay_analyzer/`:

| Archivo | Qué hace en una frase |
|--------|------------------------|
| `__init__.py` | Define qué se “exporta” del paquete (funciones y errores que otros pueden usar). |
| `__main__.py` | Permite ejecutar el paquete con `python -m rl_replay_analyzer partida.replay`. |
| `main.py` | Lógica de la línea de comandos: argumentos, llamar al parser y escribir el JSON. |
| `parser.py` | Orquesta todo: abre el `.replay`, usa boxcars o el parser propio, y devuelve equipos y goles. |
| `header_parser.py` | Lee solo la cabecera del archivo `.replay` en Python puro (sin Rust). |
| `utils.py` | Funciones auxiliares: convertir frames a tiempo, buscar propiedades en los datos del replay. |
| `exceptions.py` | Definición de los tipos de error propios del analizador. |

A continuación se detalla **cada archivo y cada función**.

---

## 1. `Analizar_Replay.pyw`

Es el programa que se abre con **doble clic**. Usa la librería **tkinter** (ventanas de escritorio en Python) para pedir un archivo y mostrar mensajes.

- **`import os, sys, json, tkinter...`**  
  Importa lo necesario: rutas de archivos, sistema, JSON y ventanas/diálogos.

- **`carpeta_proyecto = os.path.dirname(os.path.abspath(__file__))`**  
  Obtiene la carpeta donde está este script (el proyecto). Así Python encuentra el módulo `rl_replay_analyzer` aunque ejecutes el `.pyw` desde otra ubicación.

- **`sys.path.insert(0, carpeta_proyecto)`**  
  Añade esa carpeta al “path” de Python para que pueda importar `rl_replay_analyzer`.

- **`def main():`**  
  Función principal que:
  1. Crea una ventana oculta de tkinter y la pone encima.
  2. Abre el diálogo **“Elige archivo”** con `filedialog.askopenfilename`: título, carpeta inicial (Demos de Rocket League), y filtro para archivos `.replay`.
  3. Si el usuario cancela (`not archivo`), muestra “No elegiste ningún archivo” y termina.
  4. Llama a `parse_replay_file(archivo)` del módulo `rl_replay_analyzer` para analizar el replay. Si hay error, muestra un mensaje de error y termina.
  5. Construye la ruta de `resultado.json` **en la misma carpeta que el replay** (`carpeta_replay`), escribe el resultado con `json.dump` (con indentación y permitiendo caracteres como ñ).
  6. Muestra un mensaje “Listo” con la ruta del JSON, los nombres de equipos y el número de goles.
  7. Abre la carpeta del replay con `os.startfile(carpeta_replay)` para que veas el `resultado.json`.

- **`if __name__ == "__main__": main()`**  
  Solo ejecuta `main()` cuando ejecutas este archivo directamente (por ejemplo con doble clic), no cuando otro código lo importa.

---

## 2. `Analizar Replay (doble clic).bat`

Es un script de **Windows (batch)**.

- **`@echo off`**  
  No muestra por pantalla los comandos que ejecuta.

- **`cd /d "%~dp0"`**  
  Cambia al directorio donde está el `.bat` (la carpeta del proyecto).

- **`pythonw "%~dp0Analizar_Replay.pyw"`**  
  Ejecuta el script Python **sin abrir ventana de consola** (`pythonw`). `%~dp0` es la ruta de la carpeta del bat.

- **`if errorlevel 1 ... python ... pause`**  
  Si `pythonw` falla (por ejemplo Python no está en el PATH), intenta con `python` y hace una pausa para que puedas leer el error.

---

## 3. `requirements.txt`

Lista las dependencias del proyecto. Por ahora solo hay comentarios: el parser del replay está en Python puro. Si en el futuro se usa `boxcars-py`, se añadiría aquí. No hay que “saber” funciones; solo que `pip install -r requirements.txt` lee este archivo e instala lo que ponga.

---

## 4. Carpeta `rl_replay_analyzer/` — módulo principal

### 4.1. `__init__.py`

Hace que Python trate la carpeta como un **paquete** y define qué se expone al hacer `from rl_replay_analyzer import ...`.

- **`__version__ = "0.1.0"`**  
  Número de versión del paquete.

- **`from rl_replay_analyzer.parser import parse_replay_file, extract_match_data`**  
  Importa las dos funciones principales del parser.

- **`from rl_replay_analyzer.exceptions import ...`**  
  Importa los tipos de error propios.

- **`__all__ = [...]`**  
  Lista de nombres que se exportan cuando alguien hace `from rl_replay_analyzer import *`. Incluye `parse_replay_file`, `extract_match_data` y las excepciones.

---

### 4.2. `__main__.py`

- **`from rl_replay_analyzer.main import main`**  
  Importa la función `main` del módulo `main.py`.

- **`if __name__ == "__main__": raise SystemExit(main())`**  
  Cuando ejecutas el paquete con `python -m rl_replay_analyzer`, Python ejecuta este archivo. Llama a `main()` y sale con el código de retorno que devuelva (0 = éxito, 1 = error). Así la consola y scripts pueden saber si el programa terminó bien o mal.

---

### 4.3. `main.py` — Línea de comandos (CLI)

Este archivo se encarga de **recibir los argumentos** (ruta del replay, archivo de salida, indentación) y de **escribir el JSON** o mostrar errores.

- **`argparse.ArgumentParser(...)`**  
  Crea el “parser de argumentos”: define qué opciones acepta el programa (replay, `-o`, `--indent`).

- **`parser.add_argument("replay", type=Path, ...)`**  
  Primer argumento posicional: la ruta del archivo `.replay`.

- **`parser.add_argument("-o", "--output", ...)`**  
  Argumento opcional para indicar dónde guardar el JSON. Si no se pone, luego se usa `resultado.json` en el directorio actual.

- **`parser.add_argument("--indent", type=int, default=2, ...)`**  
  Indentación del JSON (0 = todo en una línea, 2 = legible).

- **`args = parser.parse_args()`**  
  Lee lo que el usuario escribió en la consola y lo guarda en `args`.

- **`out_path = args.output or Path("resultado.json")`**  
  Si no se indicó `-o`, el archivo de salida es `resultado.json` en la carpeta actual.

- **`try: result = parse_replay_file(args.replay)`**  
  Llama al parser con la ruta del replay. Si lanza excepciones propias (`InvalidReplayError`, `CorruptReplayError`, `MissingDataError`, `ReplayAnalyzerError`), las captura, imprime el mensaje en stderr y devuelve 1.

- **`with open(out_path, "w", encoding="utf-8") as f: json.dump(...)`**  
  Abre el archivo de salida en modo escritura, con codificación UTF-8, y escribe el diccionario `result` en formato JSON. Si falla (por permisos, disco, etc.), captura `OSError`, imprime error y devuelve 1.

- **`print(f"Resultado guardado en: {out_path}"); return 0`**  
  Si todo va bien, imprime la ruta del archivo y devuelve 0 (éxito).

---

### 4.4. `parser.py` — Orquestador del análisis

Este archivo **abre el archivo .replay**, decide si usar **boxcars** (si está instalado) o el **parser en Python puro** (header), y devuelve el diccionario con `teams` y `goals`.

- **`_replay_to_dict(replay)`**  
  Convierte el objeto “replay” (que puede venir de boxcars como objeto con atributos, o ya ser un diccionario) en un **diccionario** que el resto del código sabe usar. Si es `None`, lanza `CorruptReplayError`. Si es dict, lo devuelve. Si tiene `__dict__`, usa `vars(replay)`. Si tiene método `get`, lo convierte en dict. Si no, intenta construir un dict con atributos conocidos (`properties`, `tick_marks`, `keyframes`, etc.) o serializar a JSON como último recurso. Así el resto del código siempre trabaja con una estructura uniforme.

- **`_get_team_names(replay_dict)`**  
  Extrae los nombres del equipo **azul** y **naranja** desde la propiedad **TeamNames** del header. Esa propiedad suele ser una lista de dos elementos (azul, naranja); cada uno puede ser un string o una estructura con un string dentro. Usa `get_prop` para obtener la propiedad y `first_string_from_header_prop` para sacar el primer string de cada elemento. Si no hay nombre, usa "Local" y "Visitante". Devuelve una tupla `(blue_name, orange_name)`.

- **`_parse_goals_from_property(replay_dict, blue_name, orange_name)`**  
  Busca la propiedad **Goals** del header. Cada gol suele tener **Frame** (número de frame) y **Team** o **TeamIndex** (0 = azul, 1 = naranja). Recorre cada entrada, extrae frame y equipo, convierte el frame a tiempo en formato "mm:ss" con `keyframes_to_time_mapper` y `seconds_to_mm_ss`, y construye la lista de diccionarios `{"time": "mm:ss", "team": nombre}`. Si no hay propiedad Goals o está vacía, devuelve lista vacía (el llamador usará tick_marks como respaldo).

- **`_parse_goals_from_tick_marks(replay_dict, blue_name, orange_name)`**  
  **Respaldo** cuando no hay propiedad Goals: usa **tick_marks** (marcas temporales del replay). Filtra las que tienen "goal" en la descripción, toma el frame de cada una, lo convierte a "mm:ss" y añade un gol con equipo "Unknown" (en tick_marks no suele venir el equipo). Devuelve la lista de goles.

- **`extract_match_data(replay_dict)`**  
  Función principal de extracción: recibe el replay ya como diccionario (ya parseado por boxcars o por el header_parser).  
  1. Normaliza con `_replay_to_dict`.  
  2. Obtiene nombres de equipos con `_get_team_names`.  
  3. Intenta goles con `_parse_goals_from_property`; si no hay, usa `_parse_goals_from_tick_marks`.  
  4. Ordena los goles por tiempo (y por equipo si empatan).  
  5. Devuelve `{"teams": {"blue": ..., "orange": ...}, "goals": [...]}`.

- **`parse_replay_file(path)`**  
  Es la función que usa el resto del proyecto (el .pyw y la CLI).  
  1. Convierte `path` a `Path` y comprueba que el archivo exista y que la extensión sea `.replay`; si no, lanza `InvalidReplayError`.  
  2. Lee todo el archivo en binario (`open(..., "rb").read()`). Si falla, lanza `InvalidReplayError`.  
  3. Intenta importar `boxcars_py.parse_replay`. Si no está instalado (ImportError), usa el parser en Python puro: importa `parse_header` de `header_parser`, le pasa los bytes, y devuelve `extract_match_data(header_dict)`.  
  4. Si boxcars está instalado, llama a `parse_replay(data)`; si falla o devuelve None, lanza `CorruptReplayError`.  
  5. Devuelve `extract_match_data(replay)`.

---

### 4.5. `header_parser.py` — Parser del header en Python puro

Este archivo **lee solo la parte inicial (header)** del archivo `.replay` siguiendo el formato no oficial del replay de Rocket League. No usa Rust ni boxcars; todo es Python y lectura de bytes.

- **Clase `_Stream`**  
  Simula un “cursor” sobre un bloque de bytes para leer números y cadenas en formato **little-endian** (como guarda el juego).

  - **`__init__(self, data)`**  
    Guarda los bytes y la posición inicial (0).

  - **`remaining()`**  
    Devuelve cuántos bytes quedan desde la posición actual hasta el final.

  - **`read(n)`**  
    Lee los siguientes `n` bytes y avanza la posición. Si no hay suficientes bytes, lanza `CorruptReplayError`.

  - **`read_i32()`, `read_u32()`, `read_u64()`**  
    Lee un entero de 32 bits con signo, 32 sin signo o 64 sin signo (usando el módulo `struct`).

  - **`read_f32()`**  
    Lee un número de coma flotante de 32 bits.

  - **`skip_i32()`, `skip_u32()`, `advance(n)`**  
    Avanzan la posición sin devolver valor (para saltar datos que no nos interesan).

- **`_read_string8(s)`**  
  Lee un string en formato “String8”: primero un entero de 32 bits (longitud), luego esos bytes en UTF-8. Si hay un byte null al final, lo quita. Si la longitud es ridícula, lanza error. Devuelve la cadena en texto.

- **`_read_string16(s)`**  
  Lee un string “String16”: un entero de 32 bits con signo. Si es positivo, son tantos bytes en codificación Windows-1252; si es negativo, son tantos pares de bytes en UTF-16. Quita nulls al final y decodifica. Devuelve la cadena.

- **`_read_property_value(s, prop_type)`**  
  Según el tipo de propiedad (`IntProperty`, `FloatProperty`, `StrProperty`, `NameProperty`, `BoolProperty`, `QWordProperty`, `ByteProperty`, `ArrayProperty`, `StructProperty`, `EnumProperty`), lee el valor correspondiente del stream y lo devuelve. Para arrays y structs llama a otras funciones. Si el tipo no está soportado, lanza error.

- **`_skip_property_value(s, prop_type)`**  
  Igual que arriba pero **no guarda** el valor; solo avanza el cursor. Sirve para saltar propiedades que no necesitamos (por ejemplo structs muy complejos).

- **`_skip_properties(s)`**  
  Lee propiedades una a una (nombre con String8, tipo, 8 bytes que se saltan, valor según tipo) hasta encontrar la clave "None", que indica fin del bloque de propiedades.

- **`_read_properties(s)`**  
  Igual que skip pero **guardando** cada propiedad como par (nombre, valor) en una lista. Salta propiedades cuyo nombre está en `_SKIP_KEYS` (p. ej. PlayerStats, HighLights) para evitar structs complejos. Se detiene al leer "None" o tras leer la propiedad "Goals" (porque después vienen datos más complejos que no necesitamos para equipos y goles).

- **`_read_array_property(s)`**  
  Lee una propiedad de tipo array: un entero (cantidad de elementos) y luego esa cantidad de bloques de propiedades. Cada bloque se lee con `_read_properties`. Devuelve una lista de listas de (nombre, valor).

- **`parse_header(data)`**  
  Función principal del header.  
  1. Comprueba que haya suficientes bytes.  
  2. Crea un `_Stream` sobre `data` y lee el tamaño del header y salta el CRC.  
  3. Valida que el tamaño sea razonable y lee el bloque del header.  
  4. Lee versión (major, minor) y si aplica un entero más (net_version).  
  5. Lee el “game type” como string (longitud + bytes).  
  6. Lee la lista de propiedades con `_read_properties`.  
  7. Convierte esa lista en un diccionario por nombre y también la deja como lista.  
  8. Devuelve un dict con `"properties"` (en formato que entiende el resto del código), `"keyframes": []` y `"tick_marks": []` (vacíos; el parser puro no lee el cuerpo del replay).

- **`extract_team_names_from_header_dict(header_dict)`**  
  Toma el resultado de `parse_header` y extrae los nombres azul y naranja usando `get_prop(header_dict, "TeamNames")` y `first_string_from_header_prop` sobre los dos elementos del array. Si no hay TeamNames, lanza error. Por defecto usa "Blue" y "Orange".

- **`extract_goals_from_header_dict(header_dict, blue_name, orange_name)`**  
  Toma el header ya parseado y los nombres de equipos, busca la propiedad "Goals", recorre cada entrada extrayendo Frame y Team/TeamIndex, convierte el frame a tiempo con **30 FPS** (`frame/30` segundos → "mm:ss") y devuelve la lista de goles. (En el flujo actual esta función no se usa desde parser.py porque parser usa `extract_match_data` sobre el dict devuelto por `parse_header`, que ya tiene el formato de “properties”; la extracción de goles la hace `_parse_goals_from_property` en parser.py.)

---

### 4.6. `utils.py` — Utilidades

Funciones reutilizables para tiempo y para navegar por las propiedades del replay.

- **`REPLAY_FPS = 30`**  
  Constante: los replays de Rocket League suelen ir a 30 imágenes por segundo. Se usa para convertir “número de frame” en “segundos de partido”.

- **`frame_to_seconds(frame, fps)`**  
  Convierte un número de frame en segundos: `frame / fps`. Por defecto fps=30.

- **`seconds_to_mm_ss(seconds)`**  
  Convierte segundos (puede ser decimal) en una cadena "mm:ss" con dos dígitos en minutos y segundos (ej. "04:23", "00:05"). Redondea a entero.

- **`frame_to_mm_ss(frame, fps)`**  
  Combina las dos anteriores: frame → segundos → "mm:ss".

- **`get_prop(replay_data, key)`**  
  Busca en el replay una propiedad por nombre (p. ej. "TeamNames", "Goals"). El replay puede tener una clave `"properties"` que es una lista de pares [nombre, valor]. Recorre esa lista y devuelve el valor cuyo nombre coincida con `key`. Si no existe, devuelve `None`.

- **`first_string_from_header_prop(prop_value)`**  
  Dado un valor de propiedad (que puede ser un string, un dict con "Str"/"Name", una lista, una tupla, etc.), busca **el primer string** que encuentre dentro de esa estructura. Sirve para sacar el nombre del equipo cuando el formato es anidado (p. ej. array de un elemento con un string dentro).

- **`keyframes_to_time_mapper(keyframes)`**  
  Construye una **función** que convierte “número de frame” → “tiempo en segundos”. Si hay lista de keyframes (cada uno con "frame" y "time"), ordena por frame y usa interpolación entre keyframes para mayor precisión. Si no hay keyframes, la función devuelta usa simplemente frame/30. Así el resto del código siempre llama a “una función que dado un frame devuelve segundos”.

---

### 4.7. `exceptions.py` — Errores propios

Define **cuatro clases de excepciones** para que el programa pueda distinguir tipos de fallo y mostrar mensajes claros (y para que quien use el módulo pueda capturarlos).

- **`ReplayAnalyzerError(Exception)`**  
  Clase base de todos los errores del analizador. Hereda de la clase estándar `Exception`. No añade lógica; solo sirve para poder capturar “cualquier error del analizador” con un solo `except ReplayAnalyzerError`.

- **`InvalidReplayError(ReplayAnalyzerError)`**  
  Se lanza cuando el archivo no es válido: no existe, no es `.replay`, o no se puede leer.

- **`CorruptReplayError(ReplayAnalyzerError)`**  
  Se lanza cuando el archivo parece un replay pero está corrupto o el parser (boxcars o header) no puede interpretarlo correctamente.

- **`MissingDataError(ReplayAnalyzerError)`**  
  Se lanza cuando faltan datos esperados en el replay (por ejemplo no hay TeamNames o información necesaria para equipos/goles).

Todas tienen `pass` en el cuerpo porque solo queremos dar un nombre y una jerarquía; el mensaje se pasa al crear la excepción: `raise InvalidReplayError("Archivo no encontrado: ...")`.

---

## Errores que puedes recibir

| Excepción | Significado |
|-----------|-------------|
| **InvalidReplayError** | El archivo no existe, no es `.replay` o no se puede leer. |
| **CorruptReplayError** | El replay está dañado o el formato no es el esperado. |
| **MissingDataError** | Falta metadata necesaria (p. ej. nombres de equipos). |

Todas heredan de **ReplayAnalyzerError**, así que puedes capturar cualquier error del analizador con `except ReplayAnalyzerError`.

---

## Estructura de carpetas del proyecto

```
Contador/
├── .gitignore              # Archivos/carpetas que Git ignora (resultados, __pycache__, etc.)
├── README.md                # Este archivo
├── requirements.txt         # Dependencias de Python
├── ejemplo_resultado.json   # Ejemplo del JSON generado
├── Analizar_Replay.pyw      # Programa con ventana (doble clic)
├── Analizar Replay (doble clic).bat
└── rl_replay_analyzer/
    ├── __init__.py          # Exporta parse_replay_file, extract_match_data y excepciones
    ├── __main__.py          # Permite python -m rl_replay_analyzer
    ├── main.py              # CLI (argumentos y escritura del JSON)
    ├── parser.py            # parse_replay_file, extract_match_data, lógica de equipos/goles
    ├── header_parser.py     # Parser del header en Python puro
    ├── utils.py             # Tiempo (mm:ss) y helpers de propiedades
    └── exceptions.py        # ReplayAnalyzerError, InvalidReplayError, etc.
```

Los archivos `resultado.json` y `resultado_*.json` están en `.gitignore` para no subirlos a Git (cada uno genera el suyo al analizar).

---

## Uso como módulo (para tu API o backend)

Si quieres usar el analizador desde otro programa en Python:

```python
from pathlib import Path
from rl_replay_analyzer import parse_replay_file, ReplayAnalyzerError, MissingDataError

try:
    result = parse_replay_file(Path("partida.replay"))
    # result["teams"]["blue"], result["teams"]["orange"]
    # result["goals"] -> [{"time": "04:23", "team": "..."}, ...]
except ReplayAnalyzerError as e:
    # Manejar error (archivo inválido, replay corrupto, datos faltantes)
    pass
```

Para guardar tú mismo el JSON:

```python
import json
result = parse_replay_file("partida.replay")
with open("resultado.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

---

## Subir el proyecto a Git

1. Inicializa el repositorio (si aún no lo has hecho):
   ```bash
   git init
   ```
2. El archivo **`.gitignore`** ya está configurado para no subir:
   - `resultado.json` y `resultado_*.json`
   - Carpetas `__pycache__/`, `venv/`, etc.
   - Archivos de IDE y sistema
3. Añade los archivos y haz commit:
   ```bash
   git add .
   git commit -m "Analizador de replays Rocket League - equipos y goles"
   ```
4. Crea un repositorio en GitHub (o similar) y enlázalo:
   ```bash
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   git branch -M main
   git push -u origin main
   ```

Con esto el proyecto queda listo para Git y el README explica cada archivo y cada función para quien no sepa Python.
