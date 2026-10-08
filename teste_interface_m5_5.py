#!/usr/bin/env python3
"""
NYXOS — TESTE M5.5
Interface orientada ao estado real do habitat.
"""

from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INTERFACE = BASE_DIR / "interface" / "index.html"

TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


def main() -> None:
    verificar(INTERFACE.exists(), "interface principal existe")

    texto = INTERFACE.read_text(encoding="utf-8")

    verificar(
        "data.habitat?.recursos" in texto,
        "interface consome recursos reais do habitat",
    )

    verificar(
        "recursos.processos_habitat" in texto
        and "processesHabitatList" in texto,
        "interface consome entidades reais de processos",
    )

    verificar(
        "data.delta?.ultimo" in texto
        and "deltaState" in texto,
        "interface consome o último evento Delta",
    )

    verificar(
        "HOST • LIVE" in texto
        and "60.0 FPS" not in texto,
        "interface não apresenta FPS fixo como telemetria real",
    )

    verificar(
        "function escaparHtmlUI" in texto
        and "escaparHtmlUI(String(processo.nome" in texto,
        "nomes dos processos são sanitizados antes do HTML",
    )

    verificar(
        "processActivityState" in texto
        and "OBSERVADO" in texto
        and "INDISPONÍVEL" in texto,
        "interface representa disponibilidade da observação",
    )

    verificar(
        "processCount" in texto
        and "processo.nome" in texto
        and "processo.uso_cpu_percentual" in texto
        and "processo.memoria_rss_mb" in texto,
        "interface mostra identidade e telemetria mínima do processo",
    )

    verificar(
        "function initWeather()" in texto
        and "api.open-meteo.com/v1/forecast" in texto
        and "setInterval(fetchWeather, 10 * 60 * 1000)" in texto,
        "interface atualiza a telemetria do clima automaticamente",
    )

    verificar(
        "function togglePlayMusic()" in texto
        and "https://open.spotify.com/" in texto
        and "window.open(" in texto
        and "spotifyStatus" not in texto,
        "botão de música abre o Spotify Web sem navegação destrutiva",
    )

    verificar(
        "document.body.appendChild(hub)" in texto
        and "core.style.pointerEvents = 'auto'" in texto
        and "pointercancel" in texto
        and "NYXOS_INFINITY_POSITION" in texto,
        "Infinity permanece arrastável, recuperável e seguro contra cancelamento do ponteiro",
    )

    print()
    print("=" * 64)
    print("TESTE — INTERFACE ORIENTADA AO ESTADO REAL NYXOS M5.5")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
