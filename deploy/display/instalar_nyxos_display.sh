#!/usr/bin/env bash
set -euo pipefail

NYXAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${NYXAL_DIR}"

bash deploy/display/preparar_nyxos_display.sh

echo "NyxOS Display interno preparado."
