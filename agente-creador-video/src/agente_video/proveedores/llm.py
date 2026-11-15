"""Guion, capítulos y descripción con Claude."""

from __future__ import annotations

import os
import shutil
import subprocess

import anthropic
from pydantic import BaseModel, Field

from ..config import leer_prompt


class SegmentoLimpio(BaseModel):
    id: int = Field(description="Número del segmento de la transcripción")
    texto: str = Field(description="Texto limpio; vacío si el segmento no aporta nada")


class CapituloIA(BaseModel):
    segmento: int = Field(description="Número del segmento donde empieza el capítulo")
    titulo: str


class GuionIA(BaseModel):
    titulos: list[str] = Field(description="Tres títulos; el recomendado primero")
    descripcion: str
    prompts: list[str] = Field(description="Prompts dictados en el video, completos y en orden")
    capitulos: list[CapituloIA]
    segmentos: list[SegmentoLimpio] = Field(description="Un elemento por cada segmento recibido, en el mismo orden")


class ErrorGuion(RuntimeError):
    pass


def hay_credenciales() -> bool:
    """El SDK también acepta un perfil de `ant auth login`, no solo la variable de entorno."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    if shutil.which("ant"):
        estado = subprocess.run(["ant", "auth", "status"], capture_output=True, text=True)
        return estado.returncode == 0
    return False


class GuionistaClaude:
    def __init__(self, config: dict):
        self.config = config
        self.cliente = anthropic.Anthropic()

    def generar(self, segmentos: list[dict], config: dict) -> dict:
        canal = config["canal"]
        sistema = leer_prompt("guion_tutorial.md").format(
            tono=canal["tono"], llamado_accion=canal["llamado_accion"]
        )
        transcripcion = "\n".join(
            f"[{i}] ({s['inicio']:.1f}s – {s['fin']:.1f}s) {s['texto']}" for i, s in enumerate(segmentos)
        )
        pedido = (
            f"Canal: {canal['nombre']}.\n\n"
            f"Transcripción de la grabación ({len(segmentos)} segmentos):\n\n{transcripcion}"
        )

        # Streaming: la respuesta puede ser larga y así se evitan los límites de tiempo HTTP.
        # Fallbacks: si el modelo declina por un falso positivo de seguridad,
        # la API reintenta sola con otro modelo dentro de la misma llamada.
        with self.cliente.beta.messages.stream(
            model=config["ia"]["modelo"],
            max_tokens=64000,
            output_config={"effort": config["ia"]["esfuerzo"]},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=sistema,
            messages=[{"role": "user", "content": pedido}],
            output_format=GuionIA,
        ) as stream:
            respuesta = stream.get_final_message()

        if respuesta.stop_reason == "refusal":
            detalle = respuesta.stop_details.explanation if respuesta.stop_details else ""
            raise ErrorGuion(f"Claude no generó el guion (rechazo). {detalle}")
        if respuesta.stop_reason == "max_tokens":
            raise ErrorGuion("La respuesta de Claude quedó cortada: el video es demasiado largo para una sola pasada.")
        guion: GuionIA | None = respuesta.parsed_output
        if guion is None:
            raise ErrorGuion("Claude respondió sin el formato esperado.")
        return a_guion(guion, segmentos)


def a_guion(guion: GuionIA, segmentos: list[dict]) -> dict:
    """Convierte la respuesta de Claude al formato de guion del proyecto (tiempos de la grabación)."""
    textos = {s.id: s.texto.strip() for s in guion.segmentos}
    narracion = [
        {"inicio": s["inicio"], "fin": s["fin"], "texto": textos.get(i, s["texto"])}
        for i, s in enumerate(segmentos)
    ]
    capitulos = []
    for c in sorted(guion.capitulos, key=lambda c: c.segmento):
        if 0 <= c.segmento < len(segmentos):
            inicio = 0.0 if c.segmento == 0 else segmentos[c.segmento]["inicio"]
            capitulos.append({"inicio": inicio, "titulo": c.titulo.strip()})
    return {
        "titulos": [t.strip() for t in guion.titulos],
        "descripcion": guion.descripcion.strip(),
        "prompts": [p.strip() for p in guion.prompts if p.strip()],
        "capitulos": capitulos,
        "narracion": narracion,
    }

