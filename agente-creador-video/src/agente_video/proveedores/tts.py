"""Voz sintética local con Piper (licencia MIT, voces en español disponibles).

Las voces se descargan aparte: https://huggingface.co/rhasspy/piper-voices
(por ejemplo es/es_MX/claude/high). Cada voz son dos archivos, `.onnx` y `.onnx.json`,
que deben quedar juntos. Revisa la licencia de cada voz antes de usarla en un producto.
"""

from __future__ import annotations

import wave
from pathlib import Path


class VozPiper:
    def __init__(self, modelo_onnx: str):
        if not modelo_onnx or not Path(modelo_onnx).exists():
            raise RuntimeError(
                "Modo de voz 'sintetica' sin modelo de Piper. Descarga una voz y pon su ruta "
                "en [voz] modelo_piper de config/canal.toml."
            )
        try:
            from piper import PiperVoice
        except ImportError as e:
            raise RuntimeError("Falta Piper. Instálalo con: pip install -e \".[voz]\"") from e
        self.voz = PiperVoice.load(modelo_onnx)

    def sintetizar(self, texto: str, salida_wav: str) -> None:
        with wave.open(salida_wav, "wb") as archivo:
            # El nombre del método cambió entre versiones de piper-tts.
            if hasattr(self.voz, "synthesize_wav"):
                self.voz.synthesize_wav(texto, archivo)
            else:
                self.voz.synthesize(texto, archivo)
