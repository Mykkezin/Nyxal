#!/usr/bin/env python3
"""NYXOS — adaptador STT real com faster-whisper.

Mantém o motor externo na borda. O núcleo VozNyxOS recebe somente uma
callable compatível com o contrato STT: arquivo de áudio -> texto.
"""

from __future__ import annotations

from typing import Any, Callable


class AdaptadorSTTFasterWhisperNixOS:
    """Adapta faster-whisper ao contrato STT de VozNyxOS."""

    FONTE = "adaptador_stt_faster_whisper"
    VERSAO = "5.23.0"

    def __init__(
        self,
        *,
        modelo: str = "tiny",
        idioma: str = "pt",
        device: str = "cpu",
        compute_type: str = "int8",
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.modelo_nome = modelo
        self.idioma = idioma
        self.device = device
        self.compute_type = compute_type
        self._model_factory = model_factory
        self._modelo: Any | None = None

    def __call__(self, arquivo_audio: str) -> str:
        if not isinstance(arquivo_audio, str) or not arquivo_audio.strip():
            raise ValueError("O arquivo de áudio é obrigatório.")

        modelo = self._obter_modelo()
        segmentos, _info = modelo.transcribe(
            arquivo_audio,
            language=self.idioma,
        )

        partes: list[str] = []
        for segmento in segmentos:
            texto = getattr(segmento, "text", None)
            if isinstance(texto, str) and texto.strip():
                partes.append(texto.strip())

        texto_final = " ".join(partes).strip()
        if not texto_final:
            raise RuntimeError("O faster-whisper não retornou texto.")

        return texto_final

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "modelo": self.modelo_nome,
            "idioma": self.idioma,
            "device": self.device,
            "compute_type": self.compute_type,
            "motor_carregado": self._modelo is not None,
        }

    def _obter_modelo(self) -> Any:
        if self._modelo is not None:
            return self._modelo

        factory = self._model_factory
        if factory is None:
            try:
                from faster_whisper import WhisperModel
            except Exception as erro:
                raise RuntimeError(
                    "faster-whisper não está disponível no ambiente."
                ) from erro
            factory = WhisperModel

        try:
            self._modelo = factory(
                self.modelo_nome,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as erro:
            raise RuntimeError(
                "Falha ao carregar o modelo faster-whisper."
            ) from erro

        return self._modelo


__all__ = ["AdaptadorSTTFasterWhisperNixOS"]
