#!/usr/bin/env python3
"""NYXOS — M5.21 camada de áudio PipeWire/PulseAudio.

A camada descobre dispositivos de áudio sem alterar o estado do sistema por
conta própria. A saída/entrada preferenciais podem ser fixadas por nome.
A execução de reprodução/captura fica atrás de adaptadores injetáveis para
manter o núcleo testável e não habilitar voz automaticamente no residente.
"""

from __future__ import annotations

import copy
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class DispositivoAudio:
    id: str
    nome: str
    descricao: str
    estado: str
    tipo: str


class AudioNyxOS:
    FONTE = "audio_nyxos"
    VERSAO = "5.21.0"

    def __init__(
        self,
        *,
        dispositivo_preferencial: str = "SOM-023",
        executor: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.dispositivo_preferencial = dispositivo_preferencial
        self._executor = executor or subprocess.run
        self._ultimo_estado: dict[str, Any] | None = None

    def descobrir(self) -> dict[str, Any]:
        sinks = self._pactl("list", "short", "sinks")
        sources = self._pactl("list", "short", "sources")
        saidas = self._parsear(sinks.stdout, "saida")
        entradas = self._parsear(sources.stdout, "entrada")

        preferencia = self.dispositivo_preferencial.lower()
        saida = self._selecionar(saidas, preferencia)
        entrada = self._selecionar(entradas, preferencia)

        estado = {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "dispositivo_preferencial": self.dispositivo_preferencial,
            "saida": self._serializar(saida),
            "entrada": self._serializar(entrada),
            "saidas": [self._serializar(x) for x in saidas],
            "entradas": [self._serializar(x) for x in entradas],
            "bidirecional": saida is not None and entrada is not None,
        }
        self._ultimo_estado = copy.deepcopy(estado)
        return estado

    def reproduzir(self, arquivo: str, *, dispositivo: str | None = None) -> dict[str, Any]:
        alvo = dispositivo or self._resolver_saida()
        if alvo is None:
            return self._bloqueado("saida_audio_nao_encontrada")
        resultado = self._pactl("set-default-sink", alvo.id)
        return {
            "sucesso": resultado.returncode == 0,
            "acao": "reproduzir",
            "arquivo": arquivo,
            "saida_id": alvo.id,
            "estado": "dispositivo_selecionado" if resultado.returncode == 0 else "falha",
            "execucao_voz": False,
            "mutacao_host": False,
        }

    def preparar_captura(self, *, dispositivo: str | None = None) -> dict[str, Any]:
        alvo = dispositivo or self._resolver_entrada()
        if alvo is None:
            return self._bloqueado("entrada_audio_nao_encontrada")
        resultado = self._pactl("set-default-source", alvo.id)
        return {
            "sucesso": resultado.returncode == 0,
            "acao": "preparar_captura",
            "entrada_id": alvo.id,
            "estado": "dispositivo_selecionado" if resultado.returncode == 0 else "falha",
            "captura_voz": False,
            "mutacao_host": False,
        }

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "dispositivo_preferencial": self.dispositivo_preferencial,
            "ultimo_estado": copy.deepcopy(self._ultimo_estado),
            "voz_habilitada": False,
        }

    def _resolver_saida(self) -> DispositivoAudio | None:
        return self._selecionar(
            self._parsear(
                self._pactl("list", "short", "sinks").stdout,
                "saida",
            ),
            self.dispositivo_preferencial.lower(),
        )

    def _resolver_entrada(self) -> DispositivoAudio | None:
        return self._selecionar(
            self._parsear(
                self._pactl("list", "short", "sources").stdout,
                "entrada",
            ),
            self.dispositivo_preferencial.lower(),
        )

    def _pactl(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self._executor(
            ["pactl", *args],
            check=False,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _parsear(texto: str, tipo: str) -> list[DispositivoAudio]:
        dispositivos: list[DispositivoAudio] = []
        for linha in texto.splitlines():
            partes = linha.split(None, 4)
            if len(partes) < 5:
                continue
            numero, nome, _driver, _formato, estado = partes
            dispositivos.append(
                DispositivoAudio(
                    id=nome,
                    nome=nome,
                    descricao=nome,
                    estado=estado,
                    tipo=tipo,
                )
            )
        return dispositivos

    @staticmethod
    def _selecionar(
        dispositivos: list[DispositivoAudio],
        preferencia: str,
    ) -> DispositivoAudio | None:
        for dispositivo in dispositivos:
            nome = dispositivo.nome.lower()
            if preferencia in nome:
                return dispositivo
        if preferencia == "som-023":
            for dispositivo in dispositivos:
                if dispositivo.nome.lower().startswith("bluez_"):
                    return dispositivo
        return dispositivos[0] if dispositivos else None

    @staticmethod
    def _serializar(
        dispositivo: DispositivoAudio | None,
    ) -> dict[str, Any] | None:
        if dispositivo is None:
            return None
        return {
            "id": dispositivo.id,
            "nome": dispositivo.nome,
            "descricao": dispositivo.descricao,
            "estado": dispositivo.estado,
            "tipo": dispositivo.tipo,
        }

    @staticmethod
    def _bloqueado(motivo: str) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "bloqueado",
            "motivo": motivo,
            "voz_habilitada": False,
            "mutacao_host": False,
        }


__all__ = ["AudioNyxOS", "DispositivoAudio"]
