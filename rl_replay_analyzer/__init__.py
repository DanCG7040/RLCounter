"""
Analizador de archivos .replay de Rocket League.

Extrae equipos (blue/orange) y lista de goles con tiempo exacto del marcador
desde el stream de red (network_frames), usando el evento GoalScored y SecondsRemaining.
"""

__version__ = "1.0.0"

from rl_replay_analyzer.parser import parse_replay_file, extract_match_data

__all__ = [
    "parse_replay_file",
    "extract_match_data",
]
