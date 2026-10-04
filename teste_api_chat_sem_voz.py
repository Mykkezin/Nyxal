#!/usr/bin/env python3

"""
NIXAL — SMOKE TEST DA API DE CHAT SEM VOZ

Garante que importar a API conversacional não exige carregar
Whisper ou Kokoro. Esses módulos devem ser carregados somente
quando STT/TTS forem usados.
"""

from __future__ import annotations

import sys
import types


# O núcleo real depende de Ollama, mas este smoke test não consulta modelo.
sys.modules.setdefault("ollama", types.SimpleNamespace())

for modulo in (
    "faster_whisper",
    "kokoro",
    "numpy",
    "soundfile",
):
    sys.modules.pop(modulo, None)

import nyxal_web_api


def verificar(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise AssertionError(mensagem)
    print(f"[PASS] {mensagem}")


def main() -> None:
    verificar(
        nyxal_web_api.WHISPER_MODEL is None,
        "Whisper não é inicializado no import da API",
    )

    verificar(
        nyxal_web_api.KOKORO_PIPELINE is None,
        "Kokoro não é inicializado no import da API",
    )

    verificar(
        "faster_whisper" not in sys.modules,
        "faster_whisper não é importado no modo chat",
    )

    verificar(
        "kokoro" not in sys.modules,
        "kokoro não é importado no modo chat",
    )

    verificar(
        "numpy" not in sys.modules,
        "numpy não é importado no modo chat",
    )

    verificar(
        "soundfile" not in sys.modules,
        "soundfile não é importado no modo chat",
    )

    verificar(
        nyxal_web_api.HOST == "127.0.0.1",
        "host padrão da API permanece local",
    )

    verificar(
        nyxal_web_api.PORT == 8010,
        "porta padrão da API permanece 8010",
    )

    print()
    print("=" * 64)
    print("SMOKE TEST — API CHAT SEM VOZ")
    print("=" * 64)
    print("PASSOU: True")
    print("=" * 64)


if __name__ == "__main__":
    main()
