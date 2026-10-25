#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${NYXAL_PIPECAT_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/nyxal-voice-pipecat/venv}"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERRO: python3 não foi encontrado." >&2
  exit 1
fi

"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Pipecat exige Python 3.11 ou superior.")
print(f"Python compatível: {sys.version.split()[0]}")
PY

if [[ ! -f /usr/include/portaudio.h && ! -f /usr/local/include/portaudio.h ]]; then
  echo "ERRO: falta o cabeçalho de desenvolvimento portaudio.h; o PyAudio não pode compilar." >&2
  echo "Instale a dependência do sistema e execute este instalador novamente:" >&2
  echo "  sudo apt update && sudo apt install -y portaudio19-dev python3-dev build-essential" >&2
  exit 1
fi
if ! ldconfig -p 2>/dev/null | grep -q 'libportaudio'; then
  echo "ERRO: a biblioteca PortAudio ainda não aparece no linker." >&2
  echo "Execute: sudo apt install -y portaudio19-dev" >&2
  exit 1
fi

mkdir -p "$(dirname "$VENV")"
if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
if ! "$VENV/bin/python" -m pip install -r "$ROOT/deploy/voice/requirements-pipecat.txt"; then
  echo "ERRO: instalação opcional falhou. Consulte as dependências de PortAudio acima." >&2
  exit 1
fi

"$VENV/bin/python" - <<'PY'
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.whisper.stt import WhisperSTTService
from pipecat.transports.local.audio import LocalAudioTransport
print("OK: Pipecat, transporte de áudio local, Whisper, Silero VAD e Kokoro importados.")
print("Os arquivos de modelo do Kokoro são baixados no primeiro uso e ficam fora do Git.")
PY

echo
echo "Instalação experimental concluída."
echo "Ambiente virtual: $VENV"
echo "Execute manualmente (com a API Nyxal ativa):"
echo "  $VENV/bin/python $ROOT/deploy/voice/nyxal_pipecat_agent.py"
echo "Este instalador não altera nem habilita serviços systemd."
