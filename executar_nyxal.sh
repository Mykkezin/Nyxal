#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${NYXAL_PYTHON:-python3}"
CHECK_ONLY=0
if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=1
elif [[ "$#" -gt 0 ]]; then
  printf 'Uso: %s [--check]\n' "$0" >&2
  exit 2
fi

cd "$ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  printf 'Nyxal: Python não encontrado (%s). Configure NYXAL_PYTHON.\n' "$PYTHON_BIN" >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c 'try: import ollama
except ImportError: import nixal_ollama_http' >/dev/null 2>&1; then
  printf 'Nyxal: cliente Ollama indisponível; verifique o adaptador HTTP local.\n' >&2
  exit 1
fi

OLLAMA_URL="${OLLAMA_HOST:-http://127.0.0.1:11434}"
if ! "$PYTHON_BIN" -c 'import json, os, urllib.request; host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/"); data=json.load(urllib.request.urlopen(host+"/api/tags", timeout=3)); model=os.environ.get("NYXAL_CONVERSATIONAL_MODEL", "qwen2:7b"); names={item.get("name") for item in data.get("models", []) if isinstance(item, dict)}; raise SystemExit(0 if model in names else 2)' >/dev/null 2>&1; then
  printf 'Nyxal: Ollama indisponível ou modelo configurado ausente em %s. Nenhum modelo será baixado.\n' "$OLLAMA_URL" >&2
  exit 1
fi
printf 'Ollama acessível; modelo %s consta no catálogo (nenhum modelo foi carregado).\n' "${NYXAL_CONVERSATIONAL_MODEL:-qwen2:7b}"

export NYXAL_API_HOST="${NYXAL_API_HOST:-127.0.0.1}"
export NYXAL_API_PORT="${NYXAL_API_PORT:-8010}"
if [[ "$NYXAL_API_HOST" != "127.0.0.1" && "$NYXAL_API_HOST" != "::1" && "$NYXAL_API_HOST" != "localhost" ]]; then
  printf 'Nyxal: por segurança, o backend local deve escutar em loopback. Host recebido: %s\n' "$NYXAL_API_HOST" >&2
  exit 1
fi
if ! "$PYTHON_BIN" -c 'import os; p=int(os.environ["NYXAL_API_PORT"]); raise SystemExit(0 if 1 <= p <= 65535 else 1)' >/dev/null 2>&1; then
  printf 'Nyxal: NYXAL_API_PORT precisa estar entre 1 e 65535.\n' >&2
  exit 1
fi
if "$PYTHON_BIN" -c 'import os,urllib.request; url="http://127.0.0.1:"+os.environ["NYXAL_API_PORT"]+"/health"; urllib.request.urlopen(url,timeout=1).read(128)' >/dev/null 2>&1; then
  printf 'Nyxal API já está saudável em http://127.0.0.1:%s/. Não será iniciado outro servidor.\n' "$NYXAL_API_PORT"
  exit 0
fi
if [[ "$CHECK_ONLY" == "1" ]]; then
  printf 'Pré-verificações concluídas. Porta local configurada: %s.\n' "$NYXAL_API_PORT"
  exit 0
fi

printf 'Nyxal API e interface: http://127.0.0.1:%s/\n' "$NYXAL_API_PORT"
printf 'Aguardando saúde da API. Encerre com Ctrl+C.\n'
"$PYTHON_BIN" nyxal_web_api.py &
API_PID=$!
cleanup() {
  kill -INT "$API_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

for _ in {1..30}; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    wait "$API_PID"
    exit $?
  fi
  if "$PYTHON_BIN" -c 'import os,urllib.request; url="http://127.0.0.1:"+os.environ.get("NYXAL_API_PORT","8010")+"/health"; urllib.request.urlopen(url,timeout=1).read(128)' >/dev/null 2>&1; then
    printf 'API saudável. Interface: http://127.0.0.1:%s/\n' "$NYXAL_API_PORT"
    wait "$API_PID"
    exit $?
  fi
  sleep 0.5
done
printf 'Nyxal: API não ficou saudável em 15 segundos; consulte o erro acima.\n' >&2
exit 1
