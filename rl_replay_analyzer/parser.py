"""
Parser de archivos .replay de Rocket League.

Extrae equipos (blue/orange) y lista de goles con tiempo EXACTO del marcador
y equipo que anotó, usando ÚNICAMENTE el stream de red (network_frames).
NO se usa header["Goals"], Frame, ni conversión frame→segundos ni tick_rate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rl_replay_analyzer.utils import seconds_to_mm_ss


def _replay_to_dict(replay: Any) -> dict:
    """Convierte el objeto replay (boxcars) a dict para acceso uniforme."""
    if replay is None:
        raise ValueError("El replay es None")
    if isinstance(replay, dict):
        return replay
    out = {}
    for name in ("properties", "network_frames", "objects", "names"):
        if hasattr(replay, name):
            val = getattr(replay, name)
            # network_frames es un objeto con .frames, no convertirlo a lista
            if name == "network_frames":
                out[name] = val
            elif hasattr(val, "__iter__") and not isinstance(val, (str, bytes)):
                try:
                    out[name] = list(val) if val is not None else []
                except Exception:
                    out[name] = val
            else:
                out[name] = val
    return out


def _extract_goals_from_network_frames(replay_dict: dict) -> list[dict]:
    """
    Extrae goles recorriendo `replay.network_frames` y leyendo el stream de red.

    Forma robusta (comprobada en este replay):
    - El tiempo REAL del marcador está en actualizaciones de
      `TAGame.GameEvent_Soccar_TA:SecondsRemaining` (attribute `Int`).
    - El gol se detecta cuando `TAGame.GameEvent_Soccar_TA:ReplicatedStatEvent`
      publica `StatEvents.Events.Goal`.
    - El equipo que anota se obtiene del atributo `Byte` de
      `TAGame.GameEvent_Soccar_TA:ReplicatedScoredOnTeam` (0/1).

    Returns:
        Lista de dicts {"seconds_remaining": int, "team_index": int | None},
        en orden cronológico del partido (primer gol primero).
    """
    objects = replay_dict.get("objects") or replay_dict.get("names") or []

    nf = replay_dict.get("network_frames")
    if nf is None:
        return []
    frames = getattr(nf, "frames", None) or (nf.get("frames") if isinstance(nf, dict) else None)
    if not frames:
        return []

    def _obj_index(name: str) -> int | None:
        try:
            return objects.index(name)
        except ValueError:
            return None

    seconds_oid = _obj_index("TAGame.GameEvent_Soccar_TA:SecondsRemaining")
    stat_oid = _obj_index("TAGame.GameEvent_Soccar_TA:ReplicatedStatEvent")
    scored_team_oid = _obj_index("TAGame.GameEvent_Soccar_TA:ReplicatedScoredOnTeam")
    goal_event_oid = _obj_index("StatEvents.Events.Goal")

    if seconds_oid is None or stat_oid is None or goal_event_oid is None:
        return []

    current_seconds_remaining: int | None = None
    current_team_index: int | None = None
    goals: list[dict] = []

    for frame in frames:
        updated = frame.get("updated_actors", []) if isinstance(frame, dict) else []

        for ua in updated:
            oid = ua.get("object_id")
            attr = ua.get("attribute")

            if oid == seconds_oid and isinstance(attr, dict):
                # SecondsRemaining suele venir como Int
                if "Int" in attr and isinstance(attr["Int"], int):
                    current_seconds_remaining = attr["Int"]
                elif "Float" in attr and isinstance(attr["Float"], (int, float)):
                    current_seconds_remaining = int(attr["Float"])

            if oid == scored_team_oid and isinstance(attr, dict):
                # En este replay viene como Byte (0/1, 255 = None)
                if "Byte" in attr and isinstance(attr["Byte"], int):
                    b = attr["Byte"]
                    current_team_index = b if b in (0, 1) else None
                elif "Int" in attr and isinstance(attr["Int"], int):
                    i = attr["Int"]
                    current_team_index = i if i in (0, 1) else None

        # Detectar goal por ReplicatedStatEvent -> StatEvents.Events.Goal
        is_goal = False
        for ua in updated:
            if ua.get("object_id") != stat_oid:
                continue
            attr = ua.get("attribute")
            if not isinstance(attr, dict):
                continue
            se = attr.get("StatEvent")
            if isinstance(se, dict) and se.get("object_id") == goal_event_oid:
                is_goal = True
                break

        if is_goal and current_seconds_remaining is not None:
            goals.append(
                {
                    "seconds_remaining": current_seconds_remaining,
                    "team_index": current_team_index,
                }
            )

    goals.sort(key=lambda g: g["seconds_remaining"], reverse=True)
    return goals


def extract_match_data(replay: Any) -> dict:
    """
    Extrae equipos y goles desde un replay ya parseado (boxcars_py).

    Los goles se obtienen ÚNICAMENTE del stream de red (network_frames),
    evento TAGame.GameEvent_Soccar_TA:GoalScored y atributo SecondsRemaining.

    Returns:
        Dict con estructura:
        {
          "teams": { "blue": str, "orange": str },
          "goals": [ { "time": "mm:ss", "team": str }, ... ]
        }
    """
    replay_dict = _replay_to_dict(replay)

    # Requisito del proyecto: blue/orange → Local/Visitante
    blue_name = "Local"
    orange_name = "Visitante"

    goals_raw = _extract_goals_from_network_frames(replay_dict)

    goals: list[dict] = []
    for g in goals_raw:
        sec_rem = g["seconds_remaining"]
        team_index = g.get("team_index")
        if team_index == 0:
            team_name = blue_name
        elif team_index == 1:
            team_name = orange_name
        else:
            team_name = "Unknown"
        goals.append({"time": seconds_to_mm_ss(sec_rem), "team": team_name})

    return {"teams": {"blue": blue_name, "orange": orange_name}, "goals": goals}


def parse_replay_file(path: str | Path) -> dict:
    """
    Abre un archivo .replay, lo parsea con boxcars_py y devuelve el resultado.

    Requiere boxcars_py instalado (y compilación con MSVC en Windows).

    Args:
        path: Ruta al archivo .replay.

    Returns:
        Dict con "teams" y "goals" listos para resultado.json.

    Raises:
        FileNotFoundError: Archivo no encontrado.
        ValueError: No es un .replay o fallo al parsear.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    if path.suffix.lower() != ".replay":
        raise ValueError(f"Se esperaba extensión .replay: {path}")

    with open(path, "rb") as f:
        data = f.read()

    # Preferir el fork mantenido (sprocket) ya que soporta replays recientes.
    try:
        from sprocket_boxcars_py import parse_replay
    except ImportError:
        try:
            from boxcars_py import parse_replay
        except ImportError as e:
            raise ImportError(
                "Se requiere boxcars_py o sprocket_boxcars_py. "
                "Recomendado: pip install sprocket-boxcars-py. "
                "En Windows necesitas Visual Studio Build Tools (MSVC)."
            ) from e

    replay = parse_replay(data)

    if replay is None:
        raise ValueError("El parser devolvió None")

    return extract_match_data(replay)
