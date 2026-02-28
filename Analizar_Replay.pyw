"""
Abrir con doble clic: elige un archivo .replay y genera resultado.json.
No hace falta usar PowerShell ni la consola.
"""

import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox

# Asegurar que el proyecto esté en el path
carpeta_proyecto = os.path.dirname(os.path.abspath(__file__))
if carpeta_proyecto not in sys.path:
    sys.path.insert(0, carpeta_proyecto)

def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    archivo = filedialog.askopenfilename(
        title="Elige el archivo .replay de Rocket League",
        initialdir=os.path.expanduser("~\\Documents\\My Games\\Rocket League\\TAGame\\Demos"),
        filetypes=[("Replay Rocket League", "*.replay"), ("Todos los archivos", "*.*")]
    )

    if not archivo:
        messagebox.showinfo("Cancelado", "No elegiste ningún archivo.")
        return

    try:
        from rl_replay_analyzer import parse_replay_file
        resultado = parse_replay_file(archivo)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo analizar el replay:\n{e}")
        return

    # Guardar resultado.json en la misma carpeta que el replay
    carpeta_replay = os.path.dirname(archivo)
    archivo_json = os.path.join(carpeta_replay, "resultado.json")
    with open(archivo_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    messagebox.showinfo(
        "Listo",
        f"Resultado guardado en:\n{archivo_json}\n\n"
        f"Equipos: {resultado['teams']['blue']} vs {resultado['teams']['orange']}\n"
        f"Goles: {len(resultado['goals'])}"
    )
    os.startfile(carpeta_replay)

if __name__ == "__main__":
    main()
