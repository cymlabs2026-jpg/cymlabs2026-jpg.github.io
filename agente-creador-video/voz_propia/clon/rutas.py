"""Rutas comunes de los scripts de clonación.

Todo el material de trabajo (tu voz, referencias, tomas generadas) va en la carpeta `trabajo/`,
que Git ignora: tu voz es un dato personal y no se sube al repositorio.
Se puede cambiar con la variable de entorno CLON_TRABAJO.
"""
import os
import pathlib

AQUI = pathlib.Path(__file__).resolve().parent
TRABAJO = pathlib.Path(os.environ.get("CLON_TRABAJO", AQUI / "trabajo"))
TEXTOS = AQUI / "textos_locucion.json"          # lo que dice la voz (cifras en palabras)
TEXTOS_SUBTITULOS = AQUI / "textos_subtitulos.json"  # lo que se lee en pantalla (cifras en dígitos)
HUELLA = TRABAJO / "huella_clon_video.npy"      # huella de tu voz para medir el parecido
REPO = AQUI.parents[1]                          # carpeta agente-creador-video
