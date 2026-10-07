#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="${HOME}/Nyxal"
VIDEO="${NYXAL_DIR}/interface/assets/nyxos-startup.mp4"
INTERFACE_URL="http://127.0.0.1:8010/"

if [[ -f "${VIDEO}" ]]; then
    if command -v mpv >/dev/null 2>&1; then
        /usr/bin/mpv \
            --no-config \
            --fs \
            --osc=no \
            --osd-level=0 \
            --cursor-autohide=always \
            --really-quiet \
            --keep-open=no \
            "${VIDEO}" || true
    else
        echo "AVISO: mpv não está instalado; vídeo de inicialização não será reproduzido." >&2
    fi
else
    echo "AVISO: vídeo de inicialização não encontrado em ${VIDEO}; abrindo a interface normalmente." >&2
fi

exec /usr/bin/xdg-open "${INTERFACE_URL}"
