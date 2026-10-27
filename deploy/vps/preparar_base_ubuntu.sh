#!/usr/bin/env bash
set -euo pipefail

STORAGE="${NYXOS_VPS_STORAGE:-${HOME}/NyxOS/VPS}"
URL="${NYXOS_VPS_BASE_IMAGE_URL:-https://cloud-images.ubuntu.com/releases/noble/release/ubuntu-24.04-server-cloudimg-amd64.img}"
TARGET="${STORAGE}/ubuntu-24.04-server-cloudimg-amd64.img"
BASE_URL="${URL%/*}"
SUMS_URL="${NYXOS_VPS_SHA256SUMS_URL:-${BASE_URL}/SHA256SUMS}"
SUMS_TMP="${STORAGE}/.SHA256SUMS.$$"
IMAGE_TMP="${TARGET}.part"
SIDECAR="${TARGET}.sha256"

if ! command -v sha256sum >/dev/null 2>&1; then
    echo "ERRO: sha256sum não encontrado; instale/recupere coreutils antes de continuar." >&2
    exit 1
fi

mkdir -p "${STORAGE}"
trap 'rm -f "${SUMS_TMP}" "${IMAGE_TMP}"' EXIT

download() {
    local url="$1"
    local destination="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -o "${destination}" "${url}"
    elif command -v wget >/dev/null 2>&1; then
        wget --tries=3 --timeout=20 -O "${destination}" "${url}"
    else
        echo "ERRO: curl ou wget é necessário." >&2
        return 1
    fi
}

echo "Obtendo a lista SHA-256 oficial:"
echo "  ${SUMS_URL}"
download "${SUMS_URL}" "${SUMS_TMP}"

FILENAME="$(basename -- "${TARGET}")"
EXPECTED="$(awk -v file="${FILENAME}" '($2 == "*" file || $2 == file) { print $1; exit }' "${SUMS_TMP}")"
if [[ ! "${EXPECTED}" =~ ^[[:xdigit:]]{64}$ ]]; then
    echo "ERRO: SHA-256 de ${FILENAME} não encontrado na lista oficial; nenhuma imagem foi instalada." >&2
    exit 1
fi

verify_sha256() {
    local file="$1"
    local expected="$2"
    local actual
    actual="$(sha256sum "${file}" | awk '{print $1}')"
    if [[ "${actual}" != "${expected}" ]]; then
        echo "ERRO: hash SHA-256 não confere para ${file}." >&2
        echo "Esperado: ${expected}" >&2
        echo "Obtido:   ${actual}" >&2
        return 1
    fi
    echo "${expected}  ${FILENAME}" > "${SIDECAR}.part"
    mv -f "${SIDECAR}.part" "${SIDECAR}"
    echo "SHA-256 OK: ${actual}"
}

if [[ -f "${TARGET}" ]]; then
    echo "Imagem base já existe; verificando contra a lista oficial atual:"
    if verify_sha256 "${TARGET}" "${EXPECTED}"; then
        echo "Imagem base Ubuntu 24.04 verificada:"
        echo "  ${TARGET}"
        exit 0
    fi
    echo "A imagem existente foi preservada sem alteração. Se for antiga, mova-a manualmente após decidir se deseja substituí-la." >&2
    exit 2
fi

echo "Baixando imagem base oficial (o arquivo atual tem aproximadamente 600 MB):"
echo "  ${URL}"
download "${URL}" "${IMAGE_TMP}"

if ! verify_sha256 "${IMAGE_TMP}" "${EXPECTED}"; then
    rm -f "${SIDECAR}.part" "${SIDECAR}"
    exit 2
fi

mv "${IMAGE_TMP}" "${TARGET}"
# Rewrite sidecar against the final canonical filename after the verified move.
printf '%s  %s\n' "${EXPECTED}" "${FILENAME}" > "${SIDECAR}"

echo "Imagem base Ubuntu 24.04 preparada e verificada por SHA-256:"
echo "  ${TARGET}"
echo "Hash registrado em:"
echo "  ${SIDECAR}"
