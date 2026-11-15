"""Convierte la transcripción en un guion limpio, con capítulos, títulos y descripción.

El guion se guarda en `guion.md`, un archivo pensado para que una persona lo lea
y lo corrija. Las etapas siguientes leen siempre ese archivo, así que cualquier
cambio que hagas antes de aprobarlo llega al video final.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..config import aplicar_glosario
from ..proyecto import Proyecto, escribir_json, leer_json
from ..tiempo import a_marca, de_marca
from . import ErrorEtapa

NOMBRE = "guion"
DESCRIPCION = "Escribir guion, capítulos y descripción"

INSTRUCCIONES = """\
> Revisa este archivo antes de aprobarlo. Puedes corregir títulos, capítulos,
> descripción, prompts y cualquier texto de la narración.
> No cambies las marcas de tiempo de la narración (las que van entre corchetes).
> Si dejas vacío el texto de un bloque, esa frase no aparece en subtítulos ni en la voz sintética.
> Cuando esté listo, ejecuta: agente-video aprobar "{carpeta}"
"""


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    segmentos = leer_json(proyecto.ruta("transcripcion.json"))
    if not segmentos:
        raise ErrorEtapa("La transcripción está vacía: ¿la grabación tiene audio?")

    guionista = servicios.guionista(config) if servicios.guionista else None
    if guionista is None:
        guion = guion_basico(segmentos)
        aviso = (
            "Sin credenciales de Claude: se usó la transcripción tal cual, sin capítulos ni descripción. "
            "Configura ANTHROPIC_API_KEY para el guion completo."
        )
        print(f"  ⚠ {aviso}")
    else:
        guion = guionista.generar(segmentos, config)
        aviso = None

    glosario = config.get("_glosario", {})
    for bloque in guion["narracion"]:
        bloque["texto"] = aplicar_glosario(bloque["texto"], glosario)

    proyecto.ruta("guion.md").write_text(a_markdown(guion, proyecto.carpeta), encoding="utf-8")
    escribir_json(proyecto.trabajo / "guion_original.json", guion)
    proyecto.aprobar("guion", False)
    return {"capitulos": len(guion["capitulos"]), "bloques": len(guion["narracion"]), "aviso": aviso}


def guion_basico(segmentos: list[dict]) -> dict:
    return {
        "titulos": [],
        "descripcion": "",
        "prompts": [],
        "capitulos": [],
        "narracion": [{"inicio": s["inicio"], "fin": s["fin"], "texto": s["texto"]} for s in segmentos],
    }


def cargar(proyecto: Proyecto) -> dict:
    """El guion vigente: el guion.md (con tus correcciones) o, si no existe, la transcripción."""
    ruta = proyecto.ruta("guion.md")
    if ruta.exists():
        return de_markdown(ruta.read_text(encoding="utf-8"))
    return guion_basico(leer_json(proyecto.ruta("transcripcion.json")))


# --- guion.md ---------------------------------------------------------------

def a_markdown(guion: dict, carpeta: Path) -> str:
    partes = ["# Guion\n", INSTRUCCIONES.format(carpeta=carpeta)]

    partes.append("## Títulos\n")
    partes += [f"{i}. {t}" for i, t in enumerate(guion["titulos"], 1)] or ["(sin títulos)"]

    partes.append("\n## Capítulos\n")
    partes += [f"- {a_marca(c['inicio'])} | {c['titulo']}" for c in guion["capitulos"]] or ["(sin capítulos)"]

    partes.append("\n## Descripción\n")
    partes.append(guion["descripcion"] or "(sin descripción)")

    partes.append("\n## Prompts\n")
    if guion["prompts"]:
        for i, p in enumerate(guion["prompts"], 1):
            partes.append(f"### Prompt {i}\n\n{p}\n")
    else:
        partes.append("(sin prompts)")

    partes.append("\n## Narración\n")
    for b in guion["narracion"]:
        partes.append(f"### [{a_marca(b['inicio'])} → {a_marca(b['fin'])}]\n\n{b['texto']}\n")
    return "\n".join(partes).rstrip() + "\n"


_VACIO = re.compile(r"^\(sin [^)]*\)$")


def _secciones(texto: str) -> dict[str, str]:
    secciones: dict[str, str] = {}
    actual = None
    for linea in texto.splitlines():
        if linea.startswith("## "):
            actual = linea[3:].strip().lower()
            secciones[actual] = ""
        elif actual is not None:
            secciones[actual] += linea + "\n"
    return secciones


def _limpio(texto: str) -> str:
    texto = texto.strip()
    return "" if _VACIO.match(texto) else texto


def de_markdown(texto: str) -> dict:
    s = _secciones(texto)

    titulos = []
    for linea in s.get("títulos", "").splitlines():
        if m := re.match(r"^\s*\d+[.)]\s+(.+)$", linea):
            titulos.append(m.group(1).strip())

    capitulos = []
    for linea in s.get("capítulos", "").splitlines():
        if m := re.match(r"^\s*-\s*([\d:.]+)\s*\|\s*(.+)$", linea):
            capitulos.append({"inicio": de_marca(m.group(1)), "titulo": m.group(2).strip()})

    prompts = [
        _limpio(p) for p in re.split(r"^### Prompt \d+\s*$", s.get("prompts", ""), flags=re.M)[1:]
    ]

    narracion = []
    bloques = re.split(r"^### \[([\d:.]+)\s*→\s*([\d:.]+)\]\s*$", s.get("narración", ""), flags=re.M)
    for i in range(1, len(bloques) - 1, 3):
        narracion.append(
            {"inicio": de_marca(bloques[i]), "fin": de_marca(bloques[i + 1]), "texto": " ".join(bloques[i + 2].split())}
        )

    return {
        "titulos": titulos,
        "descripcion": _limpio(s.get("descripción", "")),
        "prompts": [p for p in prompts if p],
        "capitulos": sorted(capitulos, key=lambda c: c["inicio"]),
        "narracion": narracion,
    }
