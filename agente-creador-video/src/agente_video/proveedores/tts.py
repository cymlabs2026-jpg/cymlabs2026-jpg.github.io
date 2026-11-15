"""Voz sintética local con Piper (licencia MIT, voces en español disponibles).

Las voces se descargan aparte: https://huggingface.co/rhasspy/piper-voices
(por ejemplo es/es_MX/claude/high). Cada voz son dos archivos, `.onnx` y `.onnx.json`,
que deben quedar juntos. Revisa la licencia de cada voz antes de usarla en un producto.
"""

from __future__ import annotations

import wave
from pathlib import Path


class VozPiper:
    def __init__(self, modelo_onnx: str, velocidad: float = 1.0, pronunciacion: dict[str, str] | None = None):
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
        self.velocidad = velocidad
        self.pronunciacion = pronunciacion or {}

    def sintetizar(self, texto: str, salida_wav: str) -> None:
        from ..config import aplicar_glosario

        texto = aplicar_glosario(texto, self.pronunciacion)
        with wave.open(salida_wav, "wb") as archivo:
            # La API cambió entre versiones de piper-tts.
            if hasattr(self.voz, "synthesize_wav"):
                from piper import SynthesisConfig

                self.voz.synthesize_wav(texto, archivo, syn_config=SynthesisConfig(length_scale=1 / self.velocidad))
            else:
                self.voz.synthesize(texto, archivo, length_scale=1 / self.velocidad)
