"""
Punto de entrada por línea de comandos para el analizador de replays.

Uso:
    python -m rl_replay_analyzer partida.replay
    python -m rl_replay_analyzer partida.replay -o resultado.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rl_replay_analyzer.parser import parse_replay_file
from rl_replay_analyzer.exceptions import (
    ReplayAnalyzerError,
    InvalidReplayError,
    CorruptReplayError,
    MissingDataError,
)


def main() -> int:
    """Ejecuta el analizador desde la CLI. Retorna 0 en éxito, 1 en error."""
    parser = argparse.ArgumentParser(
        description="Analiza un archivo .replay de Rocket League y genera resultado.json con equipos y goles."
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
    except InvalidReplayError as e:
        print(f"Error: Archivo inválido - {e}", file=sys.stderr)
        return 1
    except CorruptReplayError as e:
        print(f"Error: Replay corrupto o no parseable - {e}", file=sys.stderr)
        return 1
    except MissingDataError as e:
        print(f"Error: Faltan datos en el replay - {e}", file=sys.stderr)
        return 1
    except ReplayAnalyzerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=args.indent or None)
    except OSError as e:
        print(f"Error: No se pudo escribir {out_path} - {e}", file=sys.stderr)
        return 1

    print(f"Resultado guardado en: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
