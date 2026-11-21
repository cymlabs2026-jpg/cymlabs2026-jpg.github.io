#!/usr/bin/env bash
# Script de instalación (setup script) del entorno de la tarea programada de video.
# Se pega tal cual en el entorno de Claude Code; corre como root antes de que empiece la sesión.
# Deja todo en /opt/venv-video y los modelos en la caché de Hugging Face (~/.cache/huggingface).
set -euo pipefail
export HF_HUB_DISABLE_XET=1
command -v uv >/dev/null || pip install -q uv
command -v ffmpeg >/dev/null || (apt-get update -qq && apt-get install -y -qq ffmpeg)
if [ ! -x /opt/venv-video/bin/python ]; then uv venv -q --python 3.13 /opt/venv-video; fi
PY=/opt/venv-video/bin/python
# Torch solo para procesador (sin CUDA): descarga mucho más liviana.
uv pip install -q --python $PY --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 torchaudio==2.6.0
uv pip install -q --python $PY chatterbox-tts==0.1.7 "setuptools<81" faster-whisper==1.2.1 "av<16" \
  resemblyzer==0.1.4 utmos-pytorch==0.1.0 num2words==0.5.14 playwright==1.65.2 soundfile librosa==0.11.0
# Modelos: Chatterbox multilingüe, Whisper small y UTMOS.
$PY - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download("ResembleAI/chatterbox", allow_patterns=["ve.pt", "t3_mtl23ls_v2.safetensors", "s3gen.pt",
                  "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"])
snapshot_download("Systran/faster-whisper-small")
snapshot_download("Blinorot/UTMOS-PyTorch")
EOF
# Navegador para dibujar las escenas: usa el Chromium ya instalado en la imagen; si no existe, lo descarga.
if [ ! -x /opt/pw-browsers/chromium ] && ! ls /opt/pw-browsers/chromium-* >/dev/null 2>&1; then
  $PY -m playwright install --with-deps chromium
fi
echo "Entorno de video listo"
