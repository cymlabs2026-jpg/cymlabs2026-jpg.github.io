"""Añade la energía a las mediciones de una ronda y muestra la tabla completa."""
import json, sys, pathlib
from rutas import TEXTOS
from energia import energia
T = json.load(open(TEXTOS, encoding="utf-8"))
r = json.load(open(sys.argv[1]))
print(f"{'configuración':36s} parecido naturalidad intelig. tono(st) dinámica(dB) sílabas/s")
filas = []
for clave, bloques in r.items():
    for b, m in bloques.items():
        st, sps, din = energia(str(pathlib.Path(sys.argv[2]) / f"{clave}__{b}.wav"), T[b])
        m.update(tono=st, dinamica=din, ritmo=sps)
        filas.append((clave, m))
json.dump(r, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
for clave, m in sorted(filas, key=lambda x: -(x[1]["tono"] + x[1]["dinamica"] / 2)):
    print(f"{clave:36s} {m['parecido']:7.3f} {m['naturalidad']:9.2f} {m['inteligibilidad']:8.0%} {m['tono']:7.1f} {m['dinamica']:10.1f} {m['ritmo']:9.1f}")
