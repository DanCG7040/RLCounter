"""
Punto de entrada por línea de comandos para el analizador de replays de Rocket League.

Uso:
    python -m rl_replay_analyzer archivo.replay
    python -m rl_replay_analyzer archivo.replay -o resultado.json --indent 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rl_replay_analyzer.parser import parse_replay_file


def main() -> int:
    """Ejecuta el analizador desde la CLI. Retorna 0 en éxito, 1 en error."""
    parser = argparse.ArgumentParser(
        description="Analiza un archivo .replay de Rocket League y genera resultado.json con equipos y goles (tiempo desde network_frames)."
    )
    parser.add_argument(
        "replay",
        type=Path,
        help="Ruta al archivo .replay",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Archivo de salida JSON (por defecto: resultado.json en el directorio actual)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentación del JSON (0 = compacto). Por defecto: 2",
    )
    args = parser.parse_args()

    out_path = args.output or Path("resultado.json")

    try:
        result = parse_replay_file(args.replay)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=args.indent if args.indent else None)
    except OSError as e:
        print(f"Error: No se pudo escribir {out_path} - {e}", file=sys.stderr)
        return 1

    print(f"Resultado guardado en: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
