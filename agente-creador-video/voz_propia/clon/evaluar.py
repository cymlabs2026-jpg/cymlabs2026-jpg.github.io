"""Mide la calidad de una voz: naturalidad (UTMOS), claridad (DNSMOS) e inteligibilidad (Whisper)."""
import json, os, sys, subprocess, pathlib
from rutas import REPO, TRABAJO
import numpy as np, soundfile as sf, torch, onnxruntime as ort

sys.path.insert(0, str(REPO / "voz_propia"))
sys.path.insert(0, str(REPO / "src"))
from preparar_dataset import similitud
from agente_video.proveedores.transcriptor import TranscriptorWhisper

# Modelo DNSMOS (sig_bak_ovr.onnx, de microsoft/DNS-Challenge) en trabajo/modelos/eval/.
M = pathlib.Path(os.environ.get("CLON_MODELOS", TRABAJO / "modelos"))
from utmos_pytorch import UTMOSScoreTorch
utmos = UTMOSScoreTorch(device="cpu")   # versión sin tarjeta gráfica, validada contra la original
dnsmos = ort.InferenceSession(str(M / "eval/sig_bak_ovr.onnx"))
whisper = TranscriptorWhisper("small", "es")

def a16k(ruta):
    datos = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(ruta), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(datos, dtype=np.float32)

def medir(ruta, texto):
    x = a16k(ruta)
    with torch.no_grad():
        mos = utmos.score(torch.tensor(x).unsqueeze(0)).item()
    # DNSMOS: ventanas de 9,01 s; se promedia la nota global (OVRL).
    n = int(9.01 * 16000); notas = []
    for i in range(0, max(1, len(x) - n + 1), n // 2):
        trozo = x[i:i + n]
        if len(trozo) < n: trozo = np.pad(trozo, (0, n - len(trozo)))
        notas.append(dnsmos.run(None, {"input_1": trozo[None, :].astype(np.float32)})[0][0][2])
    oido = " ".join(s["texto"] for s in whisper.transcribir(str(ruta)))
    return {"naturalidad": round(mos, 2), "claridad": round(float(np.mean(notas)), 2),
            "inteligibilidad": round(similitud(texto, oido), 3), "segundos": round(len(x) / 16000, 1), "oido": oido}

if __name__ == "__main__":
    resultados = {}
    for ruta in sorted(pathlib.Path(sys.argv[1]).glob("*.wav")):
        clave, bloque = ruta.stem.rsplit("__", 1)
        texto = json.load(open(sys.argv[2], encoding="utf-8"))[bloque]
        resultados.setdefault(clave, {})[bloque] = medir(ruta, texto)
    json.dump(resultados, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
    filas = []
    for clave, b in resultados.items():
        nat = np.mean([v["naturalidad"] for v in b.values()]); cla = np.mean([v["claridad"] for v in b.values()])
        intel = np.mean([v["inteligibilidad"] for v in b.values()])
        filas.append((nat, clave, cla, intel))
    print(f"{'voz':28s} naturalidad  claridad  inteligibilidad")
    for nat, clave, cla, intel in sorted(filas, reverse=True):
        print(f"{clave:28s} {nat:8.2f} {cla:10.2f} {intel:12.0%}")
