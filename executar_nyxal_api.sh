#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

HOST_VALUE="${NYXAL_API_HOST:-127.0.0.1}"
PORT_VALUE="${NYXAL_API_PORT:-8010}"

echo "============================================================"
echo "NYXAL — API CONVERSACIONAL"
echo "============================================================"
echo "Endereço: http://${HOST_VALUE}:${PORT_VALUE}"
echo "Chat:     POST /api/chat"
echo "STT:      POST /api/stt"
echo "TTS:      POST /api/tts"
echo "Health:   GET  /health"
echo "============================================================"

exec python3 nyxal_web_api.py
