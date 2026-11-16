# Proceso de la locución grabada del video 01 (el audio no se sube al repositorio).
# Uso: pon tu grabación como original.mp3 en una carpeta de trabajo y ejecuta desde ahí:
#   ffmpeg -i original.mp3 -ac 1 -ar 48000 original48.wav
#   (palabras.json: tiempos por palabra con faster-whisper, word_timestamps=True)
#   python procesar_voz.py && python cortar.py
# Los tramos (en segundos) son los de esa grabación: se ajustan con la transcripción por palabra.
"""Corta la grabación en bloques (tramos en segundos de la grabación original)."""
import subprocess, sys, pathlib
pathlib.Path("bloques").mkdir(exist_ok=True)
ORIGINAL = "voz_procesada.wav"
BLOQUES = {
    "e1": [(1.90, 12.95)],
    "e2": [(13.70, 37.35)],
    "e3": [(38.05, 48.05), (52.90, 54.45)],      # se quita el primer «del 25 %»
    "e4": [(54.45, 67.75)],
    "e5": [(68.35, 78.30)],
    "e6": [(79.00, 96.30)],
    "e7": [(96.70, 102.90)],
    "e8": [(104.25, 120.66), (123.30, 125.85)],  # se quita el primer «y para la temporada de lluvias»
    "e9": [(126.20, 138.60)],
    "cierre": [(146.40, 156.80)],                # se queda el segundo intento
}
LIMPIEZA = "anull"  # la voz ya viene procesada
for nombre, tramos in BLOQUES.items():
    entradas, filtros = [], []
    for i, (a, b) in enumerate(tramos):
        entradas += ["-ss", str(a), "-to", str(b), "-i", ORIGINAL]
        # Fundidos de 20 ms en cada corte para que no se oiga un clic.
        filtros.append(f"[{i}:a]afade=t=in:d=0.02,afade=t=out:st={b - a - 0.02:.3f}:d=0.02[p{i}]")
    union = "".join(f"[p{i}]" for i in range(len(tramos)))
    filtro = ";".join(filtros) + f";{union}concat=n={len(tramos)}:v=0:a=1,{LIMPIEZA},aresample=48000[s]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *entradas, "-filter_complex", filtro, "-map", "[s]",
                    f"bloques/{nombre}.wav"], check=True)
print("ok")
