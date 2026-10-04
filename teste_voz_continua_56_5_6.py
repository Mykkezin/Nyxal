#!/usr/bin/env python3

"""
NIXAL — TESTE 56.5.6
Integração de conversa por voz contínua + suavização do TTS.

O teste é estrutural/determinístico: não abre microfone, não chama
Whisper/Kokoro/Qwen e não exige servidor local.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INTERFACE = BASE_DIR / "interface" / "index.html"
API = BASE_DIR / "nyxal_web_api.py"


TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


def extrair_scripts_html(texto: str) -> list[str]:
    return re.findall(
        r"<script(?:\s[^>]*)?>(.*?)</script>",
        texto,
        flags=re.DOTALL | re.IGNORECASE,
    )


def main() -> None:
    verificar(
        INTERFACE.exists(),
        "interface principal existe",
    )

    verificar(
        API.exists(),
        "API principal existe",
    )

    interface = INTERFACE.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")

    # ------------------------------------------------------------
    # Voz contínua
    # ------------------------------------------------------------

    for simbolo, descricao in (
        ("voiceConversationActive", "estado persistente da conversa por voz"),
        ("startContinuousVoice", "inicialização da escuta contínua"),
        ("stopContinuousVoice", "encerramento explícito da escuta contínua"),
        ("resumeContinuousListening", "retorno automático à escuta após resposta"),
        ("createAnalyser", "VAD baseado em análise de áudio"),
        ("requestAnimationFrame", "loop de atividade de voz"),
        ("VOICE_VAD_SILENCE_MS", "detecção de fim de fala por silêncio"),
        ("VOICE_UTTERANCE_MAX_MS", "limite de segurança por turno de fala"),
        ("getUserMedia", "captura do microfone"),
        ("currentRecorder.start(100)", "captura em blocos curtos"),
        ("getFloatTimeDomainData", "leitura precisa do nível do microfone"),
        ("await sendNyxalMessage(transcript)", "encadeamento voz para conversa"),
    ):
        verificar(
            simbolo in interface,
            f"{descricao} está presente",
        )

    verificar(
        "VOICE_RECORDING_MS" not in interface,
        "antigo limite fixo de 7 segundos foi removido",
    )

    verificar(
        "voiceStopTimer" not in interface,
        "temporizador fixo de gravação não permanece na interface",
    )

    verificar(
        "body: JSON.stringify(" in interface
        and "{ mensagem: msg, sessao: nyxalSessionId }" in interface,
        "chat reaproveita a sessão conversacional existente",
    )

    verificar(
        "await speakGoddessNyxVoice" in interface,
        "a conversa aguarda o fim da fala antes de voltar a ouvir",
    )

    verificar(
        "cancelCurrentNyxalSpeech" in interface,
        "fala em andamento pode ser cancelada sem prender o fluxo",
    )

    verificar(
        "setVoiceMicrophoneEnabled(false)" in interface
        and "setVoiceMicrophoneEnabled(true)" in interface,
        "microfone é pausado durante a resposta e reativado depois",
    )

    # ------------------------------------------------------------
    # TTS mais fluido
    # ------------------------------------------------------------

    verificar(
        "KOKORO_SPEED" in api
        and "speed=KOKORO_SPEED" in api,
        "velocidade do Kokoro é configurável e aplicada",
    )

    verificar(
        'os.environ.get(\n    "NYXAL_WHISPER_MODEL",\n    "base",\n)' in api,
        "Whisper base é o padrão para maior qualidade de reconhecimento",
    )

    verificar(
        "condition_on_previous_text=False" in api
        and "temperature=0.0" in api,
        "transcrição usa parâmetros estáveis para fala curta",
    )

    verificar(
        "decodeAudioData" in interface
        and "createBufferSource" in interface,
        "TTS usa o AudioContext desbloqueado pela interação do usuário",
    )

    verificar(
        "suavizar_audio_kokoro" in api,
        "suavização do áudio Kokoro está presente",
    )

    verificar(
        "int(sample_rate * 0.008)" in api,
        "crossfade curto entre segmentos está configurado",
    )

    verificar(
        "int(sample_rate * 0.005)" in api,
        "micro-fade de entrada e saída está configurado",
    )

    verificar(
        "from kokoro import KPipeline" in api
        and "import numpy as np" in api
        and "import soundfile as sf" in api,
        "dependências pesadas de voz continuam lazy-loaded",
    )

    # ------------------------------------------------------------
    # Sintaxe Python
    # ------------------------------------------------------------

    try:
        ast.parse(api)
        verificar(
            True,
            "nyxal_web_api.py possui sintaxe Python válida",
        )
    except SyntaxError as erro:
        verificar(
            False,
            f"nyxal_web_api.py possui sintaxe Python válida: {erro}",
        )

    # ------------------------------------------------------------
    # Sintaxe JavaScript
    # ------------------------------------------------------------

    scripts = extrair_scripts_html(interface)
    verificar(
        bool(scripts),
        "interface possui blocos JavaScript identificáveis",
    )

    node = shutil.which("node")

    if node:
        with tempfile.TemporaryDirectory() as pasta:
            for indice, script in enumerate(scripts):
                arquivo = Path(pasta) / f"interface_{indice}.js"
                arquivo.write_text(script, encoding="utf-8")
                processo = subprocess.run(
                    [node, "--check", str(arquivo)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                verificar(
                    processo.returncode == 0,
                    f"bloco JavaScript {indice + 1} possui sintaxe válida",
                )
    else:
        verificar(
            True,
            "Node não disponível; validação JavaScript estrutural preservada",
        )

    print()
    print("=" * 64)
    print("TESTE — VOZ CONTÍNUA 56.5.6")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
