# Proceso de la locución grabada del video 01 (el audio no se sube al repositorio).
# Uso: pon tu grabación como original.mp3 en una carpeta de trabajo y ejecuta desde ahí:
#   ffmpeg -i original.mp3 -ac 1 -ar 48000 original48.wav
#   (palabras.json: tiempos por palabra con faster-whisper, word_timestamps=True)
#   python procesar_voz.py && python cortar.py
"""Voz firme y sin respiraciones: baja solo lo que hay ENTRE palabras y aplica la cadena de locución."""
import json, subprocess
import numpy as np, soundfile as sf

x, sr = sf.read("original48.wav")
palabras = json.load(open("palabras.json"))

# 1. Envolvente: 1 donde hay palabras (con márgenes), 0,1 (−20 dB) en los huecos, rampas de 30 ms.
ANTES, DESPUES, PISO, RAMPA = 0.20, 0.15, 0.15, 0.04
env = np.full(len(x), PISO)
FRICATIVAS = tuple("sczfjSCZFJ")  # su inicio suena parecido a una respiración: más margen
for w in palabras:
    antes = 0.38 if w["w"].lstrip("¿¡\"'(").startswith(FRICATIVAS) else ANTES
    a, b = max(0, int((w["t0"] - antes) * sr)), min(len(x), int((w["t1"] + DESPUES) * sr))
    env[a:b] = 1.0
k = int(RAMPA * sr)
env = np.convolve(env, np.ones(k) / k, mode="same")  # suaviza los bordes
np.save("envolvente.npy", env)

# 2. Cadena de locución «firme».
CADENA = ",".join([
    "highpass=f=90:poles=2", "highpass=f=90:poles=2",   # retumbe y golpes de P/B
    "adeclick",                                           # clics de boca
    "bass=g=2:f=140:w=0.8",                               # cuerpo
    "equalizer=f=280:t=o:w=1:g=-2.5",                     # menos «barro»
    "equalizer=f=3200:t=o:w=1.2:g=2.5",                   # presencia
    "treble=g=1.5:f=9000",                                # aire
    "deesser=i=0.35:m=0.5:f=0.5",                         # controla las «s»
    "acompressor=threshold=-26dB:ratio=4:attack=8:release=150:makeup=5",
    "alimiter=limit=0.89:attack=3:release=50",
])
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "original48.wav", "-af", CADENA, "-ar", "48000", "con_cadena.wav"], check=True)
y, _ = sf.read("con_cadena.wav")
n = min(len(y), len(env))
sf.write("voz_procesada.wav", y[:n] * env[:n], sr)
print("ok")
