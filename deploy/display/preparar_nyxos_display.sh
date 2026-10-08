#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DISPLAY_DIR="${NYXAL_DIR}/interface/display"

if [[ ! -f "${DISPLAY_DIR}/package.json" ]]; then
  echo "ERRO: submódulo Nyxal-Display não inicializado." >&2
  echo "Execute: git submodule update --init --recursive" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERRO: npm é necessário para construir o Nyxal-Display." >&2
  exit 1
fi

cd "${DISPLAY_DIR}"
npm install --no-audit --no-fund
npm run build

echo "Nyxal-Display construído em ${DISPLAY_DIR}/dist"
