#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${NYXAL_DIR}"

git submodule update --init --recursive
bash deploy/display/preparar_nyxos_display.sh

echo "NyxOS Display preparado."
