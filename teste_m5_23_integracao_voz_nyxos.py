#!/usr/bin/env python3
"""Integração contratual M5.23 entre VozNyxOS e adaptadores reais injetáveis."""

from types import SimpleNamespace

from nixal_adaptador_stt_faster_whisper import (
    AdaptadorSTTFasterWhisperNixOS,
)
from nixal_adaptador_tts_kokoro import AdaptadorTTSKokoroNixOS
from nixal_voz_nyxos import VozNyxOS


class AudioMock:
    def descobrir(self):
        return {"bidirecional": True}

    def preparar_captura(self):
        return {"sucesso": True, "entrada_id": "entrada.teste"}

    def preparar_saida(self):
        return {"sucesso": True, "saida_id": "saida.teste"}


class ModeloFake:
    def transcribe(self, arquivo, **kwargs):
        assert arquivo == "/tmp/entrada.wav"
        assert kwargs["language"] == "pt"
        return iter([SimpleNamespace(text="Olá Nyxal")]), SimpleNamespace()


class PipelineFake:
    def __call__(self, texto, **kwargs):
        assert texto == "Olá Mykke"
        assert kwargs["voice"] == "ef_dora"
        assert kwargs["speed"] == 1.0
        return iter([SimpleNamespace(audio="AUDIO_FAKE")])


def main() -> None:
    gravacoes = []

    stt = AdaptadorSTTFasterWhisperNixOS(
        model_factory=lambda *args, **kwargs: ModeloFake()
    )
    tts = AdaptadorTTSKokoroNixOS(
        pipeline_factory=lambda **kwargs: PipelineFake(),
        writer=lambda caminho, audio, taxa: gravacoes.append(
            (caminho, audio, taxa)
        ),
    )

    voz = VozNyxOS(
        audio=AudioMock(),
        stt=stt,
        tts=tts,
    )

    preparo = voz.preparar()
    assert preparo["sucesso"] is True
    assert preparo["voz_habilitada"] is False
    assert preparo["stt_disponivel"] is True
    assert preparo["tts_disponivel"] is True

    entrada = voz.transcrever("/tmp/entrada.wav")
    assert entrada["sucesso"] is True
    assert entrada["texto"] == "Olá Nyxal"

    saida = voz.sintetizar("Olá Mykke")
    assert saida["sucesso"] is True
    assert saida["arquivo_audio"] == "/tmp/nyxos_tts.wav"
    assert gravacoes == [
        ("/tmp/nyxos_tts.wav", "AUDIO_FAKE", 24000)
    ]

    contexto = voz.contexto()
    assert contexto["voz_habilitada"] is False
    assert contexto["execucao_automatica"] is False
    assert contexto["arquitetura_modificada"] is False

    print("TESTE_M5_23_INTEGRACAO_VOZ_NYXOS_OK")
    print("VOZ_NYXOS_STT: ADAPTADOR_INJETADO")
    print("VOZ_NYXOS_TTS: ADAPTADOR_INJETADO")
    print("VOZ_AUTOMATICA: DESABILITADA")


if __name__ == "__main__":
    main()
