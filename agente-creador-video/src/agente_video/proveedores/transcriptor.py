"""Transcripción local con Whisper (faster-whisper). Gratis y sin enviar el audio a terceros."""

from __future__ import annotations


class TranscriptorWhisper:
    def __init__(self, modelo: str = "small", idioma: str = "es"):
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError(
                "Falta la transcripción local. Instálala con: pip install -e \".[transcripcion]\""
            ) from e
        # La primera vez descarga el modelo (de 75 MB a 3 GB según el tamaño elegido).
        self.modelo = WhisperModel(modelo, device="auto", compute_type="default")
        self.idioma = idioma

    def transcribir(self, audio_wav: str) -> list[dict]:
        segmentos, _info = self.modelo.transcribe(
            audio_wav, language=self.idioma, vad_filter=True, word_timestamps=True
        )
        resultado = []
        for s in segmentos:
            if not s.text.strip():
                continue
            # Los tiempos por palabra permiten saber con precisión dónde hay voz.
            palabras = [[round(w.start, 2), round(w.end, 2)] for w in (s.words or [])]
            resultado.append(
                {"inicio": round(s.start, 2), "fin": round(s.end, 2), "texto": s.text.strip(), "palabras": palabras}
            )
        return resultado
