"""
Excepciones propias del analizador de replays.

Permite manejo específico de errores (archivo inválido, replay corrupto,
datos faltantes) sin depender de excepciones genéricas.
"""


class ReplayAnalyzerError(Exception):
    """Error base del analizador de replays."""

    pass


class InvalidReplayError(ReplayAnalyzerError):
    """El archivo no es un replay válido o no se puede abrir."""

    pass


class CorruptReplayError(ReplayAnalyzerError):
    """El replay está corrupto o no se puede parsear correctamente."""

    pass


class MissingDataError(ReplayAnalyzerError):
    """Faltan datos esperados en el replay (equipos, goles, etc.)."""

    pass
