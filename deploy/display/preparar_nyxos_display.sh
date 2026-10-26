#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DISPLAY_DIR="${NYXAL_DIR}/interface/display"

if [[ ! -f "${DISPLAY_DIR}/package.json" ]]; then
  echo "ERRO: código-fonte do Display interno não encontrado." >&2
  echo "Confirme se interface/display/package.json está versionado no repositório principal." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERRO: npm é necessário para construir o Nyxal-Display." >&2
  exit 1
fi

cd "${DISPLAY_DIR}"
npm install --no-audit --no-fund
npm run build

echo "Nyxal Display interno construído em ${DISPLAY_DIR}/dist"
