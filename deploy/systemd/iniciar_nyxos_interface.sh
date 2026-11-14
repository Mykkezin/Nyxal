#!/usr/bin/env bash
set -euo pipefail

INTERFACE_URL="${NYXOS_INTERFACE_URL:-http://127.0.0.1:8010/}"
exec /usr/bin/xdg-open "${INTERFACE_URL}"
