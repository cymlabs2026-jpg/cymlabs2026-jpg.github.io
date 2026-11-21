"""Elige la mejor toma de cada bloque de la narración con tu voz clonada (opción A).

Criterios, en orden:
1. Se entiende: inteligibilidad >= 95 %.
2. Suena a tu clon: parecido >= 0,93.
3. Energía al menos como tus videos: variación de tono >= 8 semitonos y dinámica >= 10 dB.
4. Entre las que cumplen, la más natural. Si ninguna cumple 3, la de más energía entre las que cumplen 1 y 2.
"""
import json, shutil
from rutas import TEXTOS, TEXTOS_SUBTITULOS, TRABAJO

BASE = TRABAJO
r = json.load(open(BASE / "c4.json"))
T = json.load(open(TEXTOS, encoding="utf-8"))
destino = BASE / "elegidas_clon"
shutil.rmtree(destino, ignore_errors=True)
destino.mkdir()

por_revisar = []
for b in T:
    tomas = {clave: bloques[b] for clave, bloques in r.items() if b in bloques}
    basicas = {k: m for k, m in tomas.items() if m["inteligibilidad"] >= 0.95 and m["parecido"] >= 0.93}
    energicas = {k: m for k, m in basicas.items() if m["tono"] >= 8 and m["dinamica"] >= 10}
    if energicas:
        clave, m = max(energicas.items(), key=lambda kv: kv[1]["naturalidad"])
        nota = "cumple todo"
    elif basicas:
        clave, m = max(basicas.items(), key=lambda kv: kv[1]["tono"] + kv[1]["dinamica"] / 2)
        nota = "energía algo baja"
    else:
        clave, m = max(tomas.items(), key=lambda kv: kv[1]["inteligibilidad"])
        nota = "NO cumple: rehacer"
        por_revisar.append(b)
    shutil.copy(BASE / "c4" / f"{clave}__{b}.wav", destino / f"{b}.wav")
    print(f"{b:7s} {clave[-2:]} · parecido {m['parecido']:.3f} · natural {m['naturalidad']:.2f} · "
          f"intelig. {m['inteligibilidad']:.0%} · tono {m['tono']} st · dinámica {m['dinamica']} dB · {nota}")

# Subtítulos con las cifras en dígitos (los mismos de la versión anterior).
shutil.copy(TEXTOS_SUBTITULOS, destino / "textos.json")
print("bloques por rehacer:", por_revisar or "ninguno")
