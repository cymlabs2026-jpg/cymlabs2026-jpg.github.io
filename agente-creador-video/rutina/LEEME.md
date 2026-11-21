# Rutina automática de video

Superinteligencia (el asistente local) dispara una tarea programada de Claude Code por API con un encargo en JSON.
La tarea ejecuta `agente-creador-video/rutina.py`, que produce el video con la voz clonada del autor y lo entrega
en el repositorio privado `cymlabs2026-jpg/superinteligencia-videos`.

| Archivo | Para qué sirve |
|---|---|
| `../rutina.py` | Punto de entrada: encargo → video → entrega. |
| `escenas.html` | Plantilla de escenas (intro, un bloque por idea, cierre) con animaciones estilo CapCut. |
| `instalar_entorno.sh` | Script de instalación del entorno de la tarea programada. |
| `PROMPT_TAREA.md` | Texto del prompt de la tarea programada. |
| `encargo_ejemplo.json` | Encargo de prueba de 30 segundos. |

## Formato del encargo

```json
{
  "version": 1,
  "job_id": "abc-123",
  "tema": "De qué trata el video",
  "duracion_objetivo_seg": 30,
  "formato": "horizontal",
  "titulo_en_pantalla": "Título de la intro (lo que va entre *asteriscos* sale resaltado)",
  "bloques": [
    {"locucion": "Lo que dice la voz.", "pantalla": "Texto en pantalla"},
    {"locucion": "...", "pantalla": {"etiqueta": "Paso 1", "titulo": "Título", "subtitulo": "...",
                                     "puntos": ["uno", "dos"], "cifra": "28 %"}}
  ],
  "cierre": {"llamado_a_la_accion": "Lo que dice la voz al final.", "pantalla": "Texto del cierre", "enlace": "..."},
  "estilo": {"tema": "claro", "musica": true, "etiqueta": "Etiqueta de la intro"}
}
```

- `formato`: `horizontal` (16:9), `vertical` (9:16) o `cuadrado` (1:1).
- `pantalla` puede ser un texto o un objeto. Si falta, se usa la primera frase de la locución.
- `estilo.tema`: `claro` u `oscuro`. `estilo.musica`: `false` para quitar la música.
- Las cifras se pueden escribir en dígitos: la voz las lee en palabras y los subtítulos las muestran en dígitos.
- Unas 2,5 palabras por segundo: para 30 s, unas 60–70 palabras entre bloques y cierre.

## Entrega

En `resultados/<job_id>/` de la rama `claude/resultados` del repositorio privado (se crea desde `main` si no existe):

1. `video.mp4` y `subtitulos.srt` (primer commit).
2. `listo.json` (último commit; Superinteligencia puede esperar a que aparezca):

```json
{"job_id": "abc-123", "estado": "ok", "duracion_seg": 31.2, "loudness_lufs": -16.0, "bloques": 3,
 "parecido_voz_min": 0.94, "inteligibilidad_min": 0.97, "minutos_de_trabajo": 12.5, "notas": ["..."]}
```

Si algo falla: `{"job_id": ..., "estado": "error", "error": "qué pasó", "minutos_de_trabajo": ..., "notas": [...]}` y sin video.

## Voz

La referencia se lee de `voz/ref_larga.wav` del repositorio privado (o de `ref_larga.wav` en su raíz).
Nunca se copia a este repositorio. La voz lleva la marca de agua de IA de Chatterbox.

## Red del entorno

Dominios que deben estar permitidos (además de los gestores de paquetes y GitHub, que van por defecto):
`huggingface.co`, `cdn-lfs.hf.co`, `cdn-lfs-us-1.hf.co`, `us.aws.cdn.hf.co`, `cas-bridge.xethub.hf.co`,
`download.pytorch.org`, `download-r2.pytorch.org`, `fonts.googleapis.com` y `fonts.gstatic.com`.

## Prueba local sin subir nada

```bash
/opt/venv-video/bin/python rutina.py --encargo rutina/encargo_ejemplo.json --repo-privado ../../superinteligencia-videos --no-subir
```
