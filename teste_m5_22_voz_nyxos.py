#!/usr/bin/env python3
"""Teste M5.22 — ponte conversacional de voz NyxOS."""

import subprocess

from nixal_audio_nyxos import AudioNyxOS
from nixal_voz_nyxos import VozNyxOS


class AudioMock:
    def descobrir(self):
        return {"bidirecional": True}

    def preparar_captura(self):
        return {"sucesso": True, "entrada_id": "bluez_input.SOM"}

    def preparar_saida(self):
        return {"sucesso": True, "saida_id": "bluez_output.SOM"}


def testar_audio_reproducao_explicita() -> None:
    chamadas = []

    def executor(args, **kwargs):
        chamadas.append(args)
        if args[:2] == ["pactl", "list"]:
            if args[3] == "sinks":
                saida = "1 bluez_output.SOM PipeWire s16le 2ch 48000Hz RUNNING\n"
            else:
                saida = "2 bluez_input.SOM PipeWire s16le 1ch 16000Hz RUNNING\n"
            return subprocess.CompletedProcess(args, 0, stdout=saida, stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    audio = AudioNyxOS(executor=executor)

    bloqueada = audio.reproduzir("/tmp/nyxal-voz.wav")
    assert bloqueada["sucesso"] is True
    assert bloqueada["execucao_voz"] is False
    assert bloqueada["motivo"] == "execucao_fisica_nao_autorizada"
    assert not any(args[0] == "pw-play" for args in chamadas)

    executada = audio.reproduzir(
        "/tmp/nyxal-voz.wav",
        executar_fisico=True,
    )
    assert executada["sucesso"] is True
    assert executada["execucao_voz"] is True
    assert ["pw-play", "--target", "bluez_output.SOM", "/tmp/nyxal-voz.wav"] in chamadas


def main() -> None:
    testar_audio_reproducao_explicita()

    transcricoes = []
    sinteses = []

    def stt(arquivo):
        transcricoes.append(arquivo)
        return "Olá, Nyxal"

    def tts(texto):
        sinteses.append(texto)
        return "/tmp/nyxal-voz.wav"

    voz = VozNyxOS(audio=AudioMock(), stt=stt, tts=tts)

    preparo = voz.preparar()
    assert preparo["sucesso"] is True
    assert preparo["voz_habilitada"] is False
    assert preparo["entrada_id"] == "bluez_input.SOM"
    assert preparo["saida_id"] == "bluez_output.SOM"

    entrada = voz.transcrever("/tmp/entrada.wav")
    assert entrada["texto"] == "Olá, Nyxal"
    assert transcricoes == ["/tmp/entrada.wav"]

    saida = voz.sintetizar("Olá, Mykke")
    assert saida["arquivo_audio"] == "/tmp/nyxal-voz.wav"
    assert sinteses == ["Olá, Mykke"]

    bloqueada = VozNyxOS(audio=AudioMock()).transcrever("/tmp/entrada.wav")
    assert bloqueada["sucesso"] is False
    assert bloqueada["motivo"] == "motor_stt_nao_configurado"

    contexto = voz.contexto()
    assert contexto["voz_habilitada"] is False
    assert contexto["execucao_automatica"] is False
    assert contexto["arquitetura_modificada"] is False

    print("TESTE_M5_22_VOZ_NYXOS_OK")
    print("STT: INTERFACE_VALIDADA")
    print("TTS: INTERFACE_VALIDADA")
    print("AUDIO_FISICO_EXPLICITO: INTERFACE_VALIDADA")
    print("VOZ_AUTOMATICA: DESABILITADA")


if __name__ == "__main__":
    main()
