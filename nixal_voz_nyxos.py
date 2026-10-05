#!/usr/bin/env python3
"""NYXOS — M5.22 ponte conversacional de voz.

Coordena STT/TTS com a camada AudioNyxOS, sem assumir um motor externo.
Motores reais são injetados na borda; o núcleo permanece determinístico e
testável. Voz automática continua desligada até integração explícita.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from nixal_audio_nyxos import AudioNyxOS


class VozNyxOS:
    FONTE = "voz_nyxos"
    VERSAO = "5.22.0"

    def __init__(
        self,
        *,
        audio: AudioNyxOS,
        stt: Callable[[str], str] | None = None,
        tts: Callable[[str], str] | None = None,
    ) -> None:
        self.audio = audio
        self._stt = stt
        self._tts = tts
        self._ultimo_estado: dict[str, Any] | None = None

    def preparar(self) -> dict[str, Any]:
        estado_audio = self.audio.descobrir()
        if not estado_audio.get("bidirecional"):
            return self._registrar({
                "sucesso": False,
                "estado": "bloqueado",
                "motivo": "audio_bidirecional_indisponivel",
                "voz_habilitada": False,
            })
        entrada = self.audio.preparar_captura()
        saida = self.audio.preparar_saida()
        sucesso = bool(entrada.get("sucesso") and saida.get("sucesso"))
        return self._registrar({
            "sucesso": sucesso,
            "estado": "preparada" if sucesso else "falha",
            "entrada_id": entrada.get("entrada_id"),
            "saida_id": saida.get("saida_id"),
            "voz_habilitada": False,
            "stt_disponivel": self._stt is not None,
            "tts_disponivel": self._tts is not None,
        })

    def transcrever(self, arquivo_audio: str) -> dict[str, Any]:
        if self._stt is None:
            return self._registrar({
                "sucesso": False,
                "estado": "bloqueado",
                "motivo": "motor_stt_nao_configurado",
                "voz_habilitada": False,
            })
        texto = self._stt(arquivo_audio)
        return self._registrar({
            "sucesso": True,
            "estado": "transcrito",
            "arquivo_audio": arquivo_audio,
            "texto": texto,
            "voz_habilitada": False,
        })

    def sintetizar(self, texto: str) -> dict[str, Any]:
        if self._tts is None:
            return self._registrar({
                "sucesso": False,
                "estado": "bloqueado",
                "motivo": "motor_tts_nao_configurado",
                "voz_habilitada": False,
            })
        arquivo = self._tts(texto)
        return self._registrar({
            "sucesso": True,
            "estado": "sintetizado",
            "texto": texto,
            "arquivo_audio": arquivo,
            "voz_habilitada": False,
        })

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "ultimo_estado": copy.deepcopy(self._ultimo_estado),
            "voz_habilitada": False,
            "execucao_automatica": False,
            "arquitetura_modificada": False,
        }

    def _registrar(self, estado: dict[str, Any]) -> dict[str, Any]:
        self._ultimo_estado = copy.deepcopy(estado)
        return estado


__all__ = ["VozNyxOS"]
