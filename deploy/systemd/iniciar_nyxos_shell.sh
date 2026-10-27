#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="${HOME}/Nyxal"
# Abra o painel completo em uma janela normal, não em uma miniatura/kiosk sempre cobrindo os outros apps.
# O modo simplificado de voz continua disponível por configuração explícita, mas não é mais o padrão.
INTERFACE_URL="${NYXOS_INTERFACE_URL:-http://127.0.0.1:8010/}"
STARTUP_PAGE="${NYXAL_DIR}/interface/startup.html"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
LOCK_DIR="${RUNTIME_DIR}/nyxos-shell"
LOCK_FILE="${LOCK_DIR}/singleton.lock"
STARTUP_MARKER="${LOCK_DIR}/startup-video.played"
BROWSER_PROFILE="${NYXOS_BROWSER_PROFILE:-${HOME}/.config/nyxos/browser}"
API_HEALTH_URL="${NYXOS_API_HEALTH_URL:-http://127.0.0.1:8010/health}"

mkdir -p "${LOCK_DIR}" "${BROWSER_PROFILE}"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    exit 0
fi

wait_for_api() {
    local tentativa
    for tentativa in {1..40}; do
        if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 2 "${API_HEALTH_URL}" >/dev/null 2>&1; then
            return 0
        fi
        sleep 0.5
    done
    return 1
}

wait_for_api || true

find_browser() {
    if [[ -n "${NYXOS_BROWSER_BIN:-}" && -x "${NYXOS_BROWSER_BIN}" ]]; then
        printf '%s\n' "${NYXOS_BROWSER_BIN}"
        return 0
    fi

    local candidato
    for candidato in chromium chromium-browser google-chrome google-chrome-stable firefox; do
        if command -v "${candidato}" >/dev/null 2>&1; then
            command -v "${candidato}"
            return 0
        fi
    done
    return 1
}

BROWSER="$(find_browser || true)"
if [[ -z "${BROWSER}" ]]; then
    echo "ERRO: nenhum navegador compatível foi encontrado para o shell NyxOS." >&2
    exit 1
fi

# O splash é HTML/CSS/canvas local, sem dependências externas ou arquivo de vídeo.
# Reutiliza o marcador antigo para não repetir a animação na mesma sessão gráfica.
LAUNCH_URL="${INTERFACE_URL}"
# Se o destino for a página completa, pode exibir a animação local de inicialização uma vez.
if [[ "${INTERFACE_URL}" != *"modo=voz"* && -f "${STARTUP_PAGE}" && ! -f "${STARTUP_MARKER}" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        STARTUP_FILE_URL="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().as_uri())' "${STARTUP_PAGE}")"
        ENCODED_NEXT_URL="$(python3 -c 'import sys; from urllib.parse import quote; print(quote(sys.argv[1], safe=""))' "${INTERFACE_URL}")"
        if [[ -n "${STARTUP_FILE_URL}" && -n "${ENCODED_NEXT_URL}" ]]; then
            touch "${STARTUP_MARKER}"
            LAUNCH_URL="${STARTUP_FILE_URL}?next=${ENCODED_NEXT_URL}"
        fi
    else
        echo "AVISO: python3 não encontrado; abrindo a interface sem animação de inicialização." >&2
    fi
fi

# Sem --kiosk: a janela pode ser movida/minimizada e deixa de se impor sobre o desktop.
case "$(basename "${BROWSER}")" in
    firefox)
        exec "${BROWSER}" --new-window "${LAUNCH_URL}"
        ;;
    *)
        exec "${BROWSER}" \
            --new-window \
            --autoplay-policy=no-user-gesture-required \
            --no-first-run \
            --no-default-browser-check \
            --disable-session-crashed-bubble \
            --disable-infobars \
            --user-data-dir="${BROWSER_PROFILE}" \
            "${LAUNCH_URL}"
        ;;
esac
