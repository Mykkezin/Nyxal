#!/usr/bin/env python3
"""NYXOS — adaptador TTS real com Kokoro.

Mantém o motor externo na borda. O núcleo VozNyxOS recebe somente uma
callable compatível com o contrato TTS: texto -> arquivo WAV.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


class AdaptadorTTSKokoroNixOS:
    """Adapta Kokoro ao contrato TTS de VozNyxOS."""

    FONTE = "adaptador_tts_kokoro"
    VERSAO = "5.23.0"
    SAMPLE_RATE = 24000

    def __init__(
        self,
        *,
        lang_code: str = "p",
        voice: str = "ef_dora",
        speed: float = 1.0,
        diretorio_saida: str = "/tmp",
        pipeline_factory: Callable[..., Any] | None = None,
        writer: Callable[[str, Any, int], Any] | None = None,
    ) -> None:
        self.lang_code = lang_code
        self.voice = voice
        self.speed = speed
        self.diretorio_saida = Path(diretorio_saida)
        self._pipeline_factory = pipeline_factory
        self._writer = writer
        self._pipeline: Any | None = None

    def __call__(self, texto: str) -> str:
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("O texto para síntese é obrigatório.")

        pipeline = self._obter_pipeline()

        try:
            resultados = pipeline(
                texto.strip(),
                voice=self.voice,
                speed=self.speed,
            )
            resultado = next(resultados)
        except Exception as erro:
            raise RuntimeError("Falha na síntese Kokoro.") from erro

        audio = getattr(resultado, "audio", None)
        if audio is None:
            raise RuntimeError("O Kokoro não retornou áudio.")

        self.diretorio_saida.mkdir(parents=True, exist_ok=True)
        caminho = self.diretorio_saida / "nyxos_tts.wav"
        writer = self._writer or self._writer_padrao

        try:
            writer(str(caminho), audio, self.SAMPLE_RATE)
        except Exception as erro:
            raise RuntimeError("Falha ao gravar o áudio TTS.") from erro

        return str(caminho)

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "lang_code": self.lang_code,
            "voice": self.voice,
            "speed": self.speed,
            "sample_rate": self.SAMPLE_RATE,
            "motor_carregado": self._pipeline is not None,
        }

    def _obter_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        factory = self._pipeline_factory
        if factory is None:
            try:
                from kokoro import KPipeline
            except Exception as erro:
                raise RuntimeError(
                    "Kokoro não está disponível no ambiente."
                ) from erro
            factory = KPipeline

        try:
            self._pipeline = factory(
                lang_code=self.lang_code,
                device="cpu",
            )
        except Exception as erro:
            raise RuntimeError("Falha ao carregar o pipeline Kokoro.") from erro

        return self._pipeline

    @staticmethod
    def _writer_padrao(caminho: str, audio: Any, sample_rate: int) -> None:
        try:
            import soundfile as sf
        except Exception as erro:
            raise RuntimeError(
                "soundfile não está disponível para gravar o WAV."
            ) from erro

        if hasattr(audio, "detach"):
            audio = audio.detach()
        if hasattr(audio, "cpu"):
            audio = audio.cpu()
        if hasattr(audio, "numpy"):
            audio = audio.numpy()

        sf.write(caminho, audio, sample_rate)


__all__ = ["AdaptadorTTSKokoroNixOS"]
