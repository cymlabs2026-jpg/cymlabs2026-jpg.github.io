"""Línea de comandos: agente-video nuevo | procesar | aprobar | estado."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import RAIZ, cargar_env
from .etapas import ErrorEtapa
from .medios import ErrorFFmpeg
from .orquestador import NOMBRES, EsperandoAprobacion, aprobar_guion, procesar
from .proyecto import Proyecto


def main(argv: list[str] | None = None) -> int:
    # La consola de Windows no siempre usa UTF-8; así se ven bien las tildes y los símbolos.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    cargar_env()

    parser = argparse.ArgumentParser(prog="agente-video", description="Agente Creador de Video de C&M Labs")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("nuevo", help="Crea la carpeta de un video nuevo")
    p.add_argument("nombre", help='Nombre del video, p. ej. "Tutorial Claude Sheets"')
    p.add_argument("--en", type=Path, default=RAIZ / "proyectos", help="Carpeta donde crearlo")

    p = sub.add_parser("procesar", help="Ejecuta (o retoma) el proceso completo")
    p.add_argument("carpeta", type=Path)
    p.add_argument("--desde", choices=NOMBRES, help="Rehace desde esta etapa")
    p.add_argument("--hasta", choices=NOMBRES, help="Se detiene después de esta etapa")

    p = sub.add_parser("aprobar", help="Aprueba el guion (después de revisarlo) y continúa")
    p.add_argument("carpeta", type=Path)
    p.add_argument("--no-continuar", action="store_true", help="Solo aprobar, sin seguir procesando")

    p = sub.add_parser("estado", help="Muestra qué etapas están hechas")
    p.add_argument("carpeta", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.comando == "nuevo":
            proyecto = Proyecto.crear(args.en, args.nombre)
            print(f"Proyecto creado: {proyecto.carpeta}")
            print(f"1. Copia tus grabaciones de pantalla en: {proyecto.crudo}")
            print(f'2. Ejecuta:  agente-video procesar "{proyecto.carpeta}"')
        elif args.comando == "procesar":
            _procesar(Proyecto(args.carpeta), desde=args.desde, hasta=args.hasta)
        elif args.comando == "aprobar":
            proyecto = Proyecto(args.carpeta)
            datos = aprobar_guion(proyecto)
            print(f"Guion aprobado: {len(datos['narracion'])} bloques, {len(datos['capitulos'])} capítulos.")
            if not args.no_continuar:
                _procesar(proyecto)
        elif args.comando == "estado":
            _estado(Proyecto(args.carpeta))
    except EsperandoAprobacion as e:
        print(f"\n⏸  El guion está listo y espera tu revisión.\n{e}")
        return 0
    except (ErrorEtapa, ErrorFFmpeg, FileExistsError, RuntimeError) as e:
        print(f"\n✗ {e}", file=sys.stderr)
        return 1
    return 0


def _procesar(proyecto: Proyecto, **kwargs) -> None:
    if not proyecto.carpeta.exists():
        raise ErrorEtapa(f"No existe la carpeta {proyecto.carpeta}")
    procesar(proyecto, **kwargs)
    print(f"\n✓ Video listo en {proyecto.entrega}")


def _estado(proyecto: Proyecto) -> None:
    estado = proyecto.estado()
    for nombre in NOMBRES:
        hecho = estado["etapas"].get(nombre, {}).get("completada")
        print(f"  {'✓' if hecho else '·'} {nombre}")
    print(f"  Guion aprobado: {'sí' if proyecto.aprobado('guion') else 'no'}")


if __name__ == "__main__":
    sys.exit(main())
