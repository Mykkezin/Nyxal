#!/usr/bin/env bash
set -euo pipefail

STORAGE="${NYXOS_VPS_STORAGE:-${HOME}/NyxOS/VPS}"
URL="${NYXOS_VPS_BASE_IMAGE_URL:-https://cloud-images.ubuntu.com/releases/noble/release/ubuntu-24.04-server-cloudimg-amd64.img}"
TARGET="${STORAGE}/ubuntu-24.04-server-cloudimg-amd64.img"

mkdir -p "${STORAGE}"

if [[ -f "${TARGET}" ]]; then
    echo "Imagem base já existe:"
    echo "  ${TARGET}"
    exit 0
fi

if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --retry-delay 2 -o "${TARGET}.part" "${URL}"
elif command -v wget >/dev/null 2>&1; then
    wget -O "${TARGET}.part" "${URL}"
else
    echo "ERRO: curl ou wget é necessário."
    exit 1
fi

mv "${TARGET}.part" "${TARGET}"
echo "Imagem base Ubuntu 24.04 preparada:"
echo "  ${TARGET}"
