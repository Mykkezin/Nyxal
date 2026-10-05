#!/usr/bin/env python3
"""Teste M5.21 — camada de áudio NyxOS."""

from __future__ import annotations

import subprocess

from nixal_audio_nyxos import AudioNyxOS


SINKS = """749 bluez_output.F4_75_FB_E9_74_8E.1 PipeWire s16le 1ch 16000Hz RUNNING
"""
SOURCES = """802 bluez_input.F4_75_FB_E9_74_8E.0 PipeWire s16le 1ch 16000Hz SUSPENDED
"""


def executor_factory(chamadas):
    def executar(args, **kwargs):
        chamadas.append(args)
        stdout = ""
        if args[:4] == ["pactl", "list", "short", "sinks"]:
            stdout = SINKS
        elif args[:4] == ["pactl", "list", "short", "sources"]:
            stdout = SOURCES
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
    return executar


def main() -> None:
    chamadas = []
    audio = AudioNyxOS(
        dispositivo_preferencial="SOM-023",
        executor=executor_factory(chamadas),
    )

    estado = audio.descobrir()
    assert estado["sucesso"] is True
    assert estado["bidirecional"] is True
    assert estado["saida"]["id"] == "bluez_output.F4_75_FB_E9_74_8E.1"
    assert estado["entrada"]["id"] == "bluez_input.F4_75_FB_E9_74_8E.0"

    saida = audio.reproduzir("/tmp/voz.wav")
    assert saida["sucesso"] is True
    assert saida["saida_id"] == "bluez_output.F4_75_FB_E9_74_8E.1"

    entrada = audio.preparar_captura()
    assert entrada["sucesso"] is True
    assert entrada["entrada_id"] == "bluez_input.F4_75_FB_E9_74_8E.0"

    assert audio.contexto()["voz_habilitada"] is False
    assert any(
        chamada[:2] == ["pactl", "set-default-sink"]
        for chamada in chamadas
    )
    assert any(
        chamada[:2] == ["pactl", "set-default-source"]
        for chamada in chamadas
    )

    print("TESTE_M5_21_AUDIO_NYXOS_OK")
    print("SAIDA_SOM_023: DETECTADA")
    print("ENTRADA_SOM_023: DETECTADA")
    print("BIDIRECIONAL: VALIDADO")
    print("VOZ_AUTOMATICA: DESABILITADA")


if __name__ == "__main__":
    main()
