#!/usr/bin/env python3
"""Teste determinístico dos adaptadores STT/TTS M5.23."""

from types import SimpleNamespace

from nixal_adaptador_stt_faster_whisper import (
    AdaptadorSTTFasterWhisperNixOS,
)
from nixal_adaptador_tts_kokoro import AdaptadorTTSKokoroNixOS


class ModeloFake:
    def transcribe(self, arquivo, **kwargs):
        assert arquivo == "/tmp/entrada.wav"
        assert kwargs["language"] == "pt"
        return iter(
            [
                SimpleNamespace(text=" Olá"),
                SimpleNamespace(text=" Nyxal "),
            ]
        ), SimpleNamespace(language="pt")


def testar_stt() -> None:
    chamadas = []

    def factory(*args, **kwargs):
        chamadas.append((args, kwargs))
        return ModeloFake()

    adaptador = AdaptadorSTTFasterWhisperNixOS(model_factory=factory)

    assert adaptador("/tmp/entrada.wav") == "Olá Nyxal"
    assert adaptador("/tmp/entrada.wav") == "Olá Nyxal"
    assert len(chamadas) == 1
    assert chamadas[0][0] == ("tiny",)
    assert chamadas[0][1]["device"] == "cpu"
    assert chamadas[0][1]["compute_type"] == "int8"


class PipelineFake:
    def __call__(self, texto, **kwargs):
        assert texto == "Olá Nyxal"
        assert kwargs["voice"] == "ef_dora"
        assert kwargs["speed"] == 1.0
        return iter([SimpleNamespace(audio="AUDIO_FAKE")])


def testar_tts() -> None:
    gravacoes = []

    def factory(**kwargs):
        assert kwargs["lang_code"] == "p"
        assert kwargs["device"] == "cpu"
        return PipelineFake()

    def writer(caminho, audio, sample_rate):
        gravacoes.append((caminho, audio, sample_rate))

    adaptador = AdaptadorTTSKokoroNixOS(
        pipeline_factory=factory,
        writer=writer,
        diretorio_saida="/tmp",
    )

    caminho = adaptador("Olá Nyxal")

    assert caminho == "/tmp/nyxos_tts.wav"
    assert gravacoes == [
        ("/tmp/nyxos_tts.wav", "AUDIO_FAKE", 24000)
    ]


def testar_validacoes() -> None:
    stt = AdaptadorSTTFasterWhisperNixOS(
        model_factory=lambda *args, **kwargs: ModeloFake()
    )
    try:
        stt("")
    except ValueError:
        pass
    else:
        raise AssertionError("STT deveria rejeitar entrada vazia.")

    tts = AdaptadorTTSKokoroNixOS(
        pipeline_factory=lambda **kwargs: PipelineFake(),
        writer=lambda *args: None,
    )
    try:
        tts("")
    except ValueError:
        pass
    else:
        raise AssertionError("TTS deveria rejeitar entrada vazia.")


def main() -> None:
    testar_stt()
    testar_tts()
    testar_validacoes()

    print("TESTE_M5_23_ADAPTADORES_VOZ_NYXOS_OK")
    print("STT_FASTER_WHISPER: CONTRATO_VALIDADO")
    print("TTS_KOKORO: CONTRATO_VALIDADO")
    print("MOTORES: DEPENDENCIA_INJETAVEL")
    print("VOZ_AUTOMATICA: NAO_HABILITADA")


if __name__ == "__main__":
    main()
