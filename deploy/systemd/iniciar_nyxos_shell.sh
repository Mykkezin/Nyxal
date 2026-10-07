#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="${HOME}/Nyxal"
LOCK_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxos-shell"
LOCK_FILE="${LOCK_DIR}/singleton.lock"
INTERFACE_URL="http://127.0.0.1:8010/"
VIDEO="${NYXAL_DIR}/interface/assets/nyxos-startup.mp4"

mkdir -p "${LOCK_DIR}"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    exit 0
fi

# Se a interface já estiver aberta, não cria outra instância.
if pgrep -af -- "127\.0\.0\.1:8010" | grep -v "pgrep -af" >/dev/null 2>&1; then
    exit 0
fi

if [[ -f "${VIDEO}" ]] && command -v mpv >/dev/null 2>&1; then
    /usr/bin/mpv --no-config --fs --osc=no --osd-level=0 --cursor-autohide=always --really-quiet --keep-open=no "${VIDEO}" || true
fi

exec /usr/bin/xdg-open "${INTERFACE_URL}"
