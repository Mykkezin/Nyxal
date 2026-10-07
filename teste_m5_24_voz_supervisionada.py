#!/usr/bin/env python3
"""Teste M5.24 — ciclo supervisionado STT → TTS."""

from nixal_voz_nyxos import VozNyxOS


class AudioMock:
    def descobrir(self):
        return {"bidirecional": True}

    def preparar_captura(self):
        return {"sucesso": True, "entrada_id": "entrada-teste"}

    def preparar_saida(self):
        return {"sucesso": True, "saida_id": "saida-teste"}


def main() -> None:
    chamadas = []

    def stt(arquivo):
        chamadas.append(("stt", arquivo))
        return "Olá, Nyxal"

    def tts(texto):
        chamadas.append(("tts", texto))
        return "/tmp/m5_24_supervisionado.wav"

    voz = VozNyxOS(audio=AudioMock(), stt=stt, tts=tts)

    resultado = voz.executar_supervisionado("/tmp/entrada.wav")

    assert resultado["sucesso"] is True
    assert resultado["estado"] == "ciclo_supervisionado_concluido"
    assert resultado["transcricao"]["texto"] == "Olá, Nyxal"
    assert resultado["sintese"]["arquivo_audio"] == "/tmp/m5_24_supervisionado.wav"
    assert chamadas == [
        ("stt", "/tmp/entrada.wav"),
        ("tts", "Olá, Nyxal"),
    ]
    assert resultado["voz_habilitada"] is False
    assert resultado["execucao_automatica"] is False
    assert resultado["execucao_fisica"] is False

    vazio = voz.executar_supervisionado("")
    assert vazio["sucesso"] is False
    assert vazio["motivo"] == "arquivo_audio_invalido"

    sem_stt = VozNyxOS(audio=AudioMock(), tts=tts)
    bloqueado_stt = sem_stt.executar_supervisionado("/tmp/entrada.wav")
    assert bloqueado_stt["sucesso"] is False
    assert bloqueado_stt["motivo"] == "falha_stt"
    assert bloqueado_stt["transcricao"]["motivo"] == "motor_stt_nao_configurado"

    sem_tts = VozNyxOS(audio=AudioMock(), stt=stt)
    bloqueado_tts = sem_tts.executar_supervisionado("/tmp/entrada.wav")
    assert bloqueado_tts["sucesso"] is False
    assert bloqueado_tts["motivo"] == "falha_tts"
    assert bloqueado_tts["sintese"]["motivo"] == "motor_tts_nao_configurado"

    contexto = voz.contexto()
    assert contexto["versao"] == "5.24.0"
    assert contexto["voz_habilitada"] is False
    assert contexto["execucao_automatica"] is False
    assert contexto["arquitetura_modificada"] is False

    print("TESTE_M5_24_VOZ_SUPERVISIONADA_OK")
    print("STT_TTS_SUPERVISIONADOS: VALIDADO")
    print("VOZ_AUTOMATICA: DESABILITADA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
