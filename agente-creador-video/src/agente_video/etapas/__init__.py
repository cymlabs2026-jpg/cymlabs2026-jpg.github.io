"""Etapas del modo tutorial, en el orden en que se ejecutan.

Cada etapa es un módulo con `NOMBRE`, `DESCRIPCION` y
`ejecutar(proyecto, config, servicios) -> dict | None`.
Lo que devuelve se guarda en estado.json como resumen de la etapa.
"""

from __future__ import annotations


class ErrorEtapa(RuntimeError):
    """Error con un mensaje pensado para la persona que usa el agente."""
