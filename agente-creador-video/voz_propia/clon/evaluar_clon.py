"""Mide los audios clonados: naturalidad, inteligibilidad y parecido a tu voz."""
import json, sys, pathlib
import numpy as np
from rutas import HUELLA, TEXTOS
from evaluar import medir
from resemblyzer import VoiceEncoder, preprocess_wav
enc = VoiceEncoder("cpu")
huella = np.load(sys.argv[3] if len(sys.argv) > 3 else HUELLA)
T = json.load(open(TEXTOS, encoding="utf-8"))
res = {}
for ruta in sorted(pathlib.Path(sys.argv[1]).glob("*.wav")):
    clave, b = ruta.stem.rsplit("__", 1)
    m = medir(ruta, T[b])
    m["parecido"] = round(float(np.dot(enc.embed_utterance(preprocess_wav(str(ruta))), huella)), 3)
    res.setdefault(clave, {})[b] = m
json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(f"{'configuración':42s} parecido naturalidad inteligib.")
filas = sorted(((np.mean([v['parecido'] for v in b.values()]), np.mean([v['naturalidad'] for v in b.values()]),
                 np.mean([v['inteligibilidad'] for v in b.values()]), k) for k, b in res.items()), reverse=True)
for p, n, i, k in filas:
    print(f"{k:42s} {p:7.3f} {n:10.2f} {i:9.0%}")
