"""
Analizador de archivos .replay de Rocket League para partidas privadas.

Extrae nombres de equipos personalizados y lista cronológica de goles
para integración con aplicaciones web (API, MongoDB, etc.).
"""

__version__ = "0.1.0"

from rl_replay_analyzer.parser import parse_replay_file, extract_match_data
from rl_replay_analyzer.exceptions import (
    ReplayAnalyzerError,
    InvalidReplayError,
    CorruptReplayError,
    MissingDataError,
)

__all__ = [
    "parse_replay_file",
    "extract_match_data",
    "ReplayAnalyzerError",
    "InvalidReplayError",
    "CorruptReplayError",
    "MissingDataError",
]
