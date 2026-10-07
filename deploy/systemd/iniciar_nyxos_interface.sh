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

# NyxOS is the desktop shell: launch the local interface directly in
# Firefox kiosk mode instead of delegating to the system's default browser.
if command -v firefox >/dev/null 2>&1; then
    exec /usr/bin/firefox --kiosk "${INTERFACE_URL}"
fi

echo "ERRO: Firefox não encontrado; NyxOS não pode iniciar a interface em modo desktop." >&2
exit 127
