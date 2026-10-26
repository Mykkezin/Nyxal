#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="${HOME}/Nyxal"
STARTUP_PAGE="${NYXAL_DIR}/interface/startup.html"
INTERFACE_URL="${NYXOS_INTERFACE_URL:-http://127.0.0.1:8010/}"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
STARTUP_DIR="${RUNTIME_DIR}/nyxos-shell"
STARTUP_MARKER="${STARTUP_DIR}/startup-video.played"

mkdir -p "${STARTUP_DIR}"
LAUNCH_URL="${INTERFACE_URL}"

# Mantém este launcher legado alinhado ao shell principal, sem dependência de reprodutor externo.
if [[ -f "${STARTUP_PAGE}" && ! -f "${STARTUP_MARKER}" ]] && command -v python3 >/dev/null 2>&1; then
    STARTUP_FILE_URL="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().as_uri())' "${STARTUP_PAGE}")"
    ENCODED_NEXT_URL="$(python3 -c 'import sys; from urllib.parse import quote; print(quote(sys.argv[1], safe=""))' "${INTERFACE_URL}")"
    if [[ -n "${STARTUP_FILE_URL}" && -n "${ENCODED_NEXT_URL}" ]]; then
        touch "${STARTUP_MARKER}"
        LAUNCH_URL="${STARTUP_FILE_URL}?next=${ENCODED_NEXT_URL}"
    fi
elif [[ ! -f "${STARTUP_PAGE}" ]]; then
    echo "AVISO: animação de inicialização não encontrada; abrindo a interface normalmente." >&2
fi

exec /usr/bin/xdg-open "${LAUNCH_URL}"
