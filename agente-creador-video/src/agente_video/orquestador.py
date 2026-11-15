"""Ejecuta las etapas en orden, retoma donde quedó y se detiene en las aprobaciones."""

from __future__ import annotations

import time

from . import medios
from .config import cargar_config
from .etapas import ErrorEtapa, analisis, audio, entrega, guion, ingesta, montaje, subtitulos, transcripcion
from .proveedores import Servicios, servicios_por_defecto
from .proyecto import Proyecto

ETAPAS = [ingesta, transcripcion, analisis, guion, montaje, audio, subtitulos, entrega]
NOMBRES = [e.NOMBRE for e in ETAPAS]
# Antes de esta etapa hace falta tu aprobación del guion.
ETAPA_CON_APROBACION = "montaje"


class EsperandoAprobacion(Exception):
    pass


def procesar(
    proyecto: Proyecto,
    *,
    desde: str | None = None,
    hasta: str | None = None,
    servicios: Servicios | None = None,
    config: dict | None = None,
) -> None:
    medios.verificar_ffmpeg()
    config = config or cargar_config(proyecto.carpeta)
    servicios = servicios or servicios_por_defecto()

    if desde is not None:
        _validar(desde)
        # Rehacer una etapa obliga a rehacer las que dependen de ella.
        proyecto.invalidar_desde(NOMBRES[NOMBRES.index(desde):])
    ultima = NOMBRES.index(hasta) if hasta else len(ETAPAS) - 1
    if hasta:
        _validar(hasta)

    for i, etapa in enumerate(ETAPAS[: ultima + 1], 1):
        if proyecto.etapa_completada(etapa.NOMBRE):
            print(f"[{i}/{len(ETAPAS)}] {etapa.DESCRIPCION}: ya estaba hecho ✓")
            continue
        if (
            etapa.NOMBRE == ETAPA_CON_APROBACION
            and config["ia"]["aprobar_guion"]
            and not proyecto.aprobado("guion")
        ):
            raise EsperandoAprobacion(
                f"Revisa y corrige {proyecto.ruta('guion.md')}\n"
                f"Cuando esté listo, ejecuta:  agente-video aprobar \"{proyecto.carpeta}\""
            )
        print(f"[{i}/{len(ETAPAS)}] {etapa.DESCRIPCION}…", flush=True)
        inicio = time.monotonic()
        resumen = etapa.ejecutar(proyecto, config, servicios) or {}
        proyecto.marcar_etapa(etapa.NOMBRE, segundos=round(time.monotonic() - inicio, 1), **resumen)
        print(f"      listo en {time.monotonic() - inicio:.0f} s")


def aprobar_guion(proyecto: Proyecto) -> dict:
    """Valida el guion.md editado y marca el guion como aprobado."""
    if not proyecto.etapa_completada("guion"):
        raise ErrorEtapa("Todavía no hay guion: ejecuta primero  agente-video procesar.")
    datos = guion.cargar(proyecto)
    if not datos["narracion"]:
        raise ErrorEtapa("guion.md no tiene bloques de narración: ¿se borraron las marcas de tiempo?")
    proyecto.aprobar("guion")
    # Si ya se había montado con un guion anterior, lo que depende del guion se rehace.
    proyecto.invalidar_desde(["audio", "subtitulos", "entrega"])
    return datos


def _validar(nombre: str) -> None:
    if nombre not in NOMBRES:
        raise ErrorEtapa(f"Etapa desconocida: {nombre}. Opciones: {', '.join(NOMBRES)}")
