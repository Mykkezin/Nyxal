#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

HOST_VALUE="${NYXAL_API_HOST:-127.0.0.1}"
PORT_VALUE="${NYXAL_API_PORT:-8010}"

# Persistência opt-in também no modo de execução manual; respeita valor fornecido pelo operador.
export NYXAL_CONVERSATION_MEMORY_PATH="${NYXAL_CONVERSATION_MEMORY_PATH:-${HOME}/.local/share/nyxal/conversas.json}"

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
