#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NYXAL_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DISPLAY_DIR="${NYXOS_DISPLAY_DIR:-${HOME}/Nyxal-Display}"
DISPLAY_REPO="${NYXOS_DISPLAY_REPO:-git@github.com:Mykkezin/Nyxal---DISPLAY.git}"
DISPLAY_REF="${NYXOS_DISPLAY_REF:-main}"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"

if [[ "${NYXAL_DIR}" != "${HOME}/Nyxal" ]]; then
    echo "ERRO: esta instalação espera o Nyxal em ${HOME}/Nyxal." >&2
    exit 1
fi

if [[ ! -x "${NYXAL_DIR}/.venv/bin/python" ]]; then
    echo "ERRO: .venv do Nyxal não encontrado." >&2
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    echo "ERRO: git não encontrado." >&2
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "ERRO: npm não encontrado." >&2
    exit 1
fi

mkdir -p "$(dirname "${DISPLAY_DIR}")"

if [[ ! -d "${DISPLAY_DIR}/.git" ]]; then
    git clone --branch "${DISPLAY_REF}" "${DISPLAY_REPO}" "${DISPLAY_DIR}"
else
    git -C "${DISPLAY_DIR}" fetch origin "${DISPLAY_REF}"
    git -C "${DISPLAY_DIR}" checkout "${DISPLAY_REF}"
    git -C "${DISPLAY_DIR}" pull --ff-only origin "${DISPLAY_REF}"
fi

cd "${DISPLAY_DIR}"
npm install

VITE_NYXAL_API_URL="${NYXOS_NYXAL_API_URL:-http://127.0.0.1:8010}" npm run build

install -m 0644 "${SCRIPT_DIR}/nyxos-display.service" "${USER_SYSTEMD_DIR}/nyxos-display.service"
systemctl --user daemon-reload
systemctl --user enable --now nyxos-display.service

echo "Nyxal-Display instalado."
echo "Diretório: ${DISPLAY_DIR}"
echo "API Core: ${NYXOS_NYXAL_API_URL:-http://127.0.0.1:8010}"
echo "Display: http://127.0.0.1:3000/"
