#!/usr/bin/env python3
"""Teste M5.22 — ponte conversacional de voz NyxOS."""

from nixal_voz_nyxos import VozNyxOS


class AudioMock:
    def descobrir(self):
        return {"bidirecional": True}

    def preparar_captura(self):
        return {"sucesso": True, "entrada_id": "bluez_input.SOM"}

    def preparar_saida(self):
        return {"sucesso": True, "saida_id": "bluez_output.SOM"}


def main() -> None:
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
    print("VOZ_AUTOMATICA: DESABILITADA")


if __name__ == "__main__":
    main()
