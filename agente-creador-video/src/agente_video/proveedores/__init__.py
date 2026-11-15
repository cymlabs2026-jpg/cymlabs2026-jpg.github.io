"""Conectores intercambiables con servicios de IA.

Las etapas no importan estos módulos directamente: reciben un objeto `Servicios`
con lo que necesitan. Así se puede cambiar un proveedor (por ejemplo, la voz)
o usar uno falso en las pruebas sin tocar las etapas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class Transcriptor(Protocol):
    def transcribir(self, audio_wav: str) -> list[dict]:
        """Devuelve [{'inicio': s, 'fin': s, 'texto': str}, ...]."""


class Guionista(Protocol):
    def generar(self, segmentos: list[dict], config: dict) -> dict:
        """Devuelve el guion en el formato de etapas.guion."""


class Voz(Protocol):
    def sintetizar(self, texto: str, salida_wav: str) -> None: ...


@dataclass
class Servicios:
    """Fábricas perezosas: el proveedor solo se crea (e importa) si una etapa lo usa."""

    transcriptor: Callable[[dict], Transcriptor] | None = None
    guionista: Callable[[dict], Guionista | None] | None = None
    voz: Callable[[dict], Voz] | None = None


def servicios_por_defecto() -> Servicios:
    def transcriptor(config: dict):
        from .transcriptor import TranscriptorWhisper

        return TranscriptorWhisper(config["transcripcion"]["modelo_whisper"], config["canal"]["idioma"])

    def guionista(config: dict):
        from .llm import GuionistaClaude, hay_credenciales

        return GuionistaClaude(config) if hay_credenciales() else None

    def voz(config: dict):
        from .tts import VozPiper

        return VozPiper(
            config["voz"]["modelo_piper"],
            velocidad=config["voz"].get("velocidad", 1.0),
            pronunciacion=config.get("_pronunciacion", {}),
        )

    return Servicios(transcriptor=transcriptor, guionista=guionista, voz=voz)
