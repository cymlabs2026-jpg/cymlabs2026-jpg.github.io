"""Genera bloques con tu voz clonada (Chatterbox multilingüe, licencia MIT).
Uso: clonar.py <carpeta_salida> <referencia.wav|todas> <bloques separados por coma> [exageracion] [cfg] [tomas]"""
import json, sys, pathlib, torch, torchaudio
from rutas import TEXTOS, TRABAJO
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
torch.manual_seed(0)
T = json.load(open(TEXTOS, encoding="utf-8"))
PRON = {"Claude": "Clod", "C&M": "C y M"}
salida = pathlib.Path(sys.argv[1]); salida.mkdir(parents=True, exist_ok=True)
refs = sorted((TRABAJO / "referencias_video").glob("*.wav")) if sys.argv[2] == "todas" else [pathlib.Path(sys.argv[2])]
bloques = sys.argv[3].split(",")
exag = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
cfg = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
tomas = int(sys.argv[6]) if len(sys.argv) > 6 else 1
modelo = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
for ref in refs:
    for b in bloques:
        texto = T[b]
        for k, v in PRON.items():
            texto = texto.replace(k, v)
        for t in range(1, tomas + 1):
            wav = modelo.generate(texto, language_id="es", audio_prompt_path=str(ref), exaggeration=exag, cfg_weight=cfg)
            nombre = f"{ref.stem}_x{exag}_c{cfg}_t{t}__{b}.wav"
            torchaudio.save(str(salida / nombre), wav, modelo.sr)
            print("listo", nombre, flush=True)
