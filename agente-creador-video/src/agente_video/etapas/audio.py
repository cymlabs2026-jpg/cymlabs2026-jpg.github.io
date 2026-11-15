"""Arma el audio final: voz (original o sintética), música de fondo y nivel para YouTube."""

from __future__ import annotations

from pathlib import Path

from .. import medios, tiempo
from ..proyecto import Proyecto, leer_json
from . import ErrorEtapa
from . import guion as guion_etapa
from . import marca as marca_etapa

NOMBRE = "audio"
DESCRIPCION = "Voz, música y nivel de audio"

# La voz sintética puede acelerarse hasta este punto para caber en su tramo.
ACELERACION_MAXIMA_VOZ = 1.3


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    base = marca_etapa.video_base(proyecto)
    duracion = medios.duracion(base)
    entradas: list[str] = ["-i", str(base)]
    filtros: list[str] = []
    resumen: dict = {"voz": config["voz"]["modo"]}

    if config["voz"]["modo"] == "sintetica":
        plan = leer_json(proyecto.ruta("edicion.json"))["tramos"]
        etiqueta, resumen["bloques_ajustados"] = _voz_sintetica(
            proyecto, config, servicios, plan, duracion, entradas, filtros
        )
    elif config["voz"]["modo"] == "original":
        etiqueta = "[0:a]"
    else:
        raise ErrorEtapa(f"Modo de voz desconocido: {config['voz']['modo']!r} (usa 'original' o 'sintetica').")

    musica = config["musica"]["archivo"]
    if musica:
        ruta_musica = Path(musica)
        if not ruta_musica.is_absolute():
            ruta_musica = Path(config["_raiz"]) / ruta_musica
        if not ruta_musica.exists():
            raise ErrorEtapa(f"No se encontró la música: {ruta_musica}")
        indice = _contar_entradas(entradas)
        entradas += ["-stream_loop", "-1", "-i", str(ruta_musica)]
        filtros += [
            f"[{indice}:a]volume={config['musica']['volumen']},atrim=0:{duracion:.3f}[musica];",
            f"{etiqueta}asplit=2[voz][voz_control];",
            # La música baja sola cuando hay voz (sidechain) y vuelve a subir en las pausas.
            "[musica][voz_control]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=600[musica_baja];",
            "[voz][musica_baja]amix=inputs=2:normalize=0:duration=first[mezcla];",
        ]
        etiqueta = "[mezcla]"
        resumen["musica"] = ruta_musica.name

    # -14 LUFS es el nivel al que YouTube normaliza: así el video no suena bajo ni se recorta.
    filtros.append(f"{etiqueta}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[audio_final]")
    script = proyecto.trabajo / "audio_filtro.txt"
    script.write_text("\n".join(filtros), encoding="utf-8")

    proyecto.entrega.mkdir(exist_ok=True)
    medios.ffmpeg(
        *entradas,
        "-filter_complex_script", str(script),
        "-map", "0:v", "-map", "[audio_final]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{duracion:.3f}",
        str(proyecto.entrega / "video_final.mp4"),
    )
    return resumen


def _contar_entradas(entradas: list[str]) -> int:
    return entradas.count("-i")


def _voz_sintetica(proyecto, config, servicios, plan, duracion, entradas, filtros) -> tuple[str, int]:
    if servicios.voz is None:
        raise ErrorEtapa("No hay proveedor de voz configurado.")
    voz = servicios.voz(config)
    carpeta = proyecto.trabajo / "voz"
    carpeta.mkdir(exist_ok=True)

    bloques = [b for b in guion_etapa.cargar(proyecto)["narracion"] if b["texto"].strip()]
    despl = marca_etapa.desplazamiento(proyecto)
    inicios = [despl + tiempo.remapear(b["inicio"], plan) for b in bloques]
    etiquetas, ajustados = [], 0
    for i, (bloque, inicio) in enumerate(zip(bloques, inicios)):
        wav = carpeta / f"{i:03d}.wav"
        voz.sintetizar(bloque["texto"], str(wav))
        dur = medios.duracion(wav)
        siguiente = inicios[i + 1] if i + 1 < len(inicios) else duracion
        disponible = max(0.1, siguiente - inicio)
        tempo = min(dur / disponible, ACELERACION_MAXIMA_VOZ) if dur > disponible else 1.0
        if tempo > 1.0:
            ajustados += 1
        indice = _contar_entradas(entradas)
        entradas += ["-i", str(wav)]
        retardo = int(inicio * 1000)
        cadena = (medios.cadena_atempo(tempo) + ",") if tempo > 1.0 else ""
        filtros.append(f"[{indice}:a]{cadena}aresample=48000,adelay={retardo}:all=1[voz{i}];")
        etiquetas.append(f"[voz{i}]")

    if not etiquetas:
        filtros.append(f"aevalsrc=0|0:s=48000:d={duracion:.3f}[voz_sintetica];")
    else:
        filtros.append(
            f"{''.join(etiquetas)}amix=inputs={len(etiquetas)}:normalize=0:duration=longest,"
            f"apad,atrim=0:{duracion:.3f}[voz_sintetica];"
        )
    return "[voz_sintetica]", ajustados
