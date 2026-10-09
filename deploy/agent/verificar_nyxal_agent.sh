#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT}/.venv/bin/python"
[[ -x "${PYTHON_BIN}" ]] || PYTHON_BIN="$(command -v python3)"
API_BASE="${NYXAL_API_BASE:-http://127.0.0.1:8010}"
TEST_VOICE="false"
if [[ "${1:-}" == "--test-voice" ]]; then
  TEST_VOICE="true"
elif [[ $# -gt 0 ]]; then
  echo "Uso: $0 [--test-voice]" >&2
  exit 2
fi

exec "${PYTHON_BIN}" - "${API_BASE}" "${TEST_VOICE}" <<'PY'
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

base = sys.argv[1].rstrip("/")
test_voice = sys.argv[2] == "true"
failures = 0


def get_json(path: str):
    request = urllib.request.Request(
        base + path,
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise RuntimeError("resposta excedeu 2 MiB")
        return json.loads(raw.decode("utf-8"))


def check_json(label: str, path: str):
    global failures
    try:
        value = get_json(path)
        if not isinstance(value, dict):
            raise RuntimeError("resposta não é objeto JSON")
        print(f"[OK] {label}")
        return value
    except Exception as exc:
        failures += 1
        print(f"[FALHA] {label}: {type(exc).__name__}: {exc}")
        return {}


def show_config(flag: object) -> str:
    return "configurado" if flag is True else "pendente"


print(f"Nyxal preflight · {base}")
print("Nota: 'configurado' indica configuração local; não prova que o provedor remoto respondeu.")

health = check_json("Nyxal Core /health", "/health")
if health:
    print(f"  estado: {health.get('estado', '—')}")

agent = check_json("Estado do agente", "/api/agent/status")
providers = agent.get("provedores", {}) if isinstance(agent.get("provedores"), dict) else {}
for name in ("hermes", "gemini", "letta"):
    value = providers.get(name, {})
    if isinstance(value, dict):
        print(f"  {name}: {show_config(value.get('configurado'))}")

visual = agent.get("criacao_visual", {})
if isinstance(visual, dict):
    print(f"  criação visual: {show_config(visual.get('configurado'))} · modelo {visual.get('modelo', '—')}")

memory = agent.get("memoria_letta", {})
if isinstance(memory, dict):
    print(f"  memória Letta: {show_config(memory.get('configurada'))}")

whatsapp = agent.get("whatsapp", {})
if isinstance(whatsapp, dict):
    print(f"  WhatsApp: {whatsapp.get('estado', 'não informado')} · allowlist {show_config(whatsapp.get('allowlist_configurada'))}")

voice = agent.get("voz", {})
if isinstance(voice, dict):
    print(f"  voz: {voice.get('motor', '—')} · perfil {voice.get('voz_configurada', '—')}")

context = check_json("Observabilidade do host (somente leitura)", "/api/agent/contexto")
observed = context.get("observabilidade", {}) if isinstance(context.get("observabilidade"), dict) else {}
host = observed.get("host", {}) if isinstance(observed.get("host"), dict) else {}
memory_host = observed.get("memoria", {}) if isinstance(observed.get("memoria"), dict) else {}
disk = observed.get("armazenamento_home", {}) if isinstance(observed.get("armazenamento_home"), dict) else {}
processes = observed.get("processos", {}) if isinstance(observed.get("processos"), dict) else {}
print(f"  host: {host.get('hostname', '—')}")
print(f"  RAM usada: {memory_host.get('uso_percentual', '—')}% · /home: {disk.get('uso_percentual', '—')}%")
print(f"  processos observados: {processes.get('total_observado', '—')}")

google = check_json("Google Workspace OAuth", "/api/integracoes/google/status")
services = google.get("servicos_disponiveis", {}) if isinstance(google.get("servicos_disponiveis"), dict) else {}
print(f"  OAuth: {google.get('estado', '—')} · Gmail {show_config(services.get('gmail') is True)} · Agenda {show_config(services.get('agenda') is True)} · Contatos {show_config(services.get('contatos') is True)} · Drive metadata {show_config(services.get('drive_metadados') is True)}")
if google.get("proximo_passo"):
    print(f"  próximo passo Google: {google['proximo_passo']}")

try:
    request = urllib.request.Request(base + "/display/", headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=8) as response:
        content_type = response.headers.get("Content-Type", "")
        if response.status != 200 or "text/html" not in content_type:
            raise RuntimeError(f"HTTP {response.status}, Content-Type={content_type}")
        print("[OK] Nyxal Display servido em /display/")
except Exception as exc:
    failures += 1
    print(f"[FALHA] Nyxal Display /display/: {type(exc).__name__}: {exc}")
    print("  Execute: bash deploy/display/instalar_nyxos_display.sh")

if test_voice:
    try:
        body = json.dumps({"texto": "Olá, eu sou a Nyxal."}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            base + "/api/tts",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "audio/wav"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            audio = response.read(32 * 1024 * 1024 + 1)
            if response.status != 200 or not response.headers.get("Content-Type", "").startswith("audio/wav"):
                raise RuntimeError(f"resposta TTS não é WAV (HTTP {response.status})")
            if len(audio) > 32 * 1024 * 1024 or not audio.startswith(b"RIFF"):
                raise RuntimeError("resposta não contém um WAV RIFF válido")
            voice_name = voice.get("voz_configurada", "—") if isinstance(voice, dict) else "—"
            print(f"[OK] TTS gerou WAV real ({len(audio)} bytes). Voz configurada: {voice_name}")
    except urllib.error.HTTPError as exc:
        failures += 1
        try:
            message = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            message = ""
        print(f"[FALHA] TTS: HTTP {exc.code} {message}")
    except Exception as exc:
        failures += 1
        print(f"[FALHA] TTS: {type(exc).__name__}: {exc}")

print()
if failures:
    print(f"Preflight terminou com {failures} falha(s). Recursos que aparecem como pendentes exigem configuração.")
    raise SystemExit(1)
print("Preflight concluído sem falhas nos endpoints obrigatórios.")
if not test_voice:
    print("Para verificar a voz realmente, rode: bash deploy/agent/verificar_nyxal_agent.sh --test-voice")
PY
