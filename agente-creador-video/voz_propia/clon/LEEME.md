# Clonación de voz para la locución

Scripts con los que se hizo la locución del video 01 con la voz del autor clonada
(opción A: Chatterbox multilingüe, referencia larga de 26 s, exageración 0,7 y cfg 0,3).

**Tu voz no se sube a Git.** Las grabaciones, las referencias y las tomas generadas van en
`trabajo/` (ignorada por Git). La marca de agua de IA de Chatterbox queda siempre activa.
En la descripción del video conviene poner: «voz generada con IA a partir de la voz del autor».

## Qué hace cada archivo

| Archivo | Para qué sirve |
|---|---|
| `rutas.py` | Carpetas comunes (`trabajo/` o la variable `CLON_TRABAJO`). |
| `textos_locucion.json` | Lo que dice la voz en cada bloque (cifras en palabras). |
| `textos_subtitulos.json` | Lo mismo con cifras en dígitos, para los subtítulos. |
| `clonar.py` | Genera los bloques con tu voz clonada. |
| `evaluar.py` | Mide naturalidad (UTMOS), claridad (DNSMOS) e inteligibilidad (Whisper). |
| `evaluar_clon.py` | Añade el parecido con tu voz (Resemblyzer). |
| `energia.py` / `evaluar_energia.py` | Miden variación de tono, dinámica y ritmo. |
| `elegir_clon.py` | Elige la mejor toma de cada bloque y la copia a `trabajo/elegidas_clon/`. |

## Preparar (una sola vez)

1. Dos entornos de Python:
   - Para clonar: `pip install chatterbox-tts "setuptools<81"` (sin `setuptools<81` falla la marca de agua).
   - Para medir: `pip install faster-whisper "av<16" utmos-pytorch resemblyzer librosa onnxruntime "setuptools<81"`.
2. En `trabajo/` pon:
   - `referencias_largas/ref_larga.wav`: unos 25 s de tu voz limpia y con energía (se armó con trozos de dos de tus videos).
   - `huella_clon_video.npy`: la huella de tu voz (promedio de `VoiceEncoder().embed_utterance` de Resemblyzer sobre tus referencias).
   - `modelos/eval/sig_bak_ovr.onnx`: el modelo DNSMOS de Microsoft.

## Pasos

Desde esta carpeta:

```bash
python clonar.py trabajo/c4 trabajo/referencias_largas/ref_larga.wav e1,e2,e3,e4,e5,e6,e7,e8,e9,cierre 0.7 0.3 3
```

```bash
python evaluar_clon.py trabajo/c4 trabajo/c4.json
```

```bash
python evaluar_energia.py trabajo/c4.json trabajo/c4
```

```bash
python elegir_clon.py
```

Luego, desde `ejemplos/video-01-ventas-ferreteria/version_animada/`:

```bash
python renderizar.py --locucion ../../../voz_propia/clon/trabajo/elegidas_clon --musica --subtitulos --salida video_01_tu_clon.mp4
```

Usa `HF_HUB_DISABLE_XET=1` si la descarga de modelos de Hugging Face se queda colgada.
