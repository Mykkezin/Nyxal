#!/usr/bin/env python3
"""NYXOS — M5.15 presença persistente da máquina."""

from __future__ import annotations

import copy
import json
import os
import time
time
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_PADRAO = BASE_DIR / "presenca_maquina_nyxos.json"


class PresencaMaquinaNixOS:
    """Mantém um estado compacto de presença e retomada segura."""

    FONTE = "presenca_maquina_nyxos"
    VERSAO = "5.15.0"

    def __init__(
        self,
        *,
        arquivo: str | Path = ARQUIVO_PADRAO,
        diretorio_systemd: str | Path | None = None,
    ) -> None:
        self.arquivo = Path(arquivo)
        self.diretorio_systemd = Path(
            diretorio_systemd
            if diretorio_systemd is not None
            else Path.home() / ".config" / "systemd" / "user"
        )
        self._dados = self._carregar()
        self._startup_id = f"{os.getpid()}-{time.time_ns()}"

    def _estrutura(self) -> dict[str, Any]:
        return {
            "versao": self.VERSAO,
            "origem": self.FONTE,
            "estado_presenca": "inicializando",
            "startup_id": None,
            "iniciado_em": None,
            "ultimo_heartbeat": None,
            "encerrado_em": None,
            "motivo_encerramento": None,
            "retomada": {
                "detectada": False,
                "tipo": "primeira_inicializacao",
            },
            "residencia": {
                "esperada": True,
                "diretorio_systemd": str(self.diretorio_systemd),
                "unidades": {},
            },
        }

    def _carregar(self) -> dict[str, Any]:
        if not self.arquivo.is_file():
            return self._estrutura()

        try:
            dados = json.loads(
                self.arquivo.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return self._estrutura()

        if not isinstance(dados, dict):
            return self._estrutura()

        base = self._estrutura()
        base.update({
            chave: copy.deepcopy(valor)
            for chave, valor in dados.items()
            if chave in base
        })
        return base

    def _unidades(self) -> dict[str, bool]:
        nomes = (
            "nyxos.target",
            "nyxal-api.service",
            "nyxos-residente.service",
        )
        return {
            nome: (self.diretorio_systemd / nome).is_file()
            for nome in nomes
        }

    def _salvar(self) -> None:
        self.arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporario = self.arquivo.with_name(
            self.arquivo.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                self._dados,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(
            temporario,
            self.arquivo,
        )

    @staticmethod
    def _agora() -> float:
        return time.time()

    def iniciar(self, *, timestamp: float | None = None) -> dict[str, Any]:
        anterior = self._dados.get("estado_presenca")
        retomada = {
            "detectada": anterior in {
                "ativo",
                "heartbeat",
                "interrompido_inesperadamente",
            },
            "tipo": (
                "retomada_apos_reinicio"
                if anterior in {
                    "ativo",
                    "heartbeat",
                    "interrompido_inesperadamente",
                }
                else "primeira_inicializacao"
            ),
        }

        agora = self._agora() if timestamp is None else float(timestamp)
        self._dados["estado_presenca"] = "ativo"
        self._dados["startup_id"] = self._startup_id
        self._dados["iniciado_em"] = agora
        self._dados["ultimo_heartbeat"] = agora
        self._dados["encerrado_em"] = None
        self._dados["motivo_encerramento"] = None
        self._dados["retomada"] = retomada
        self._dados["residencia"]["unidades"] = self._unidades()
        self._salvar()
        return self.contexto()

    def heartbeat(
        self,
        *,
        timestamp: float | None = None,
        estado_residente: str = "executando",
    ) -> dict[str, Any]:
        agora = self._agora() if timestamp is None else float(timestamp)
        self._dados["estado_presenca"] = "heartbeat"
        self._dados["ultimo_heartbeat"] = agora
        self._dados["residencia"]["unidades"] = self._unidades()
        self._dados["residencia"]["estado_residente"] = estado_residente
        self._salvar()
        return self.contexto()

    def encerrar(
        self,
        *,
        motivo: str = "encerramento_controlado",
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        if not isinstance(motivo, str) or not motivo.strip():
            raise ValueError("motivo_encerramento_invalido")
        agora = self._agora() if timestamp is None else float(timestamp)
        self._dados["estado_presenca"] = "encerrado"
        self._dados["encerrado_em"] = agora
        self._dados["motivo_encerramento"] = motivo.strip()[:128]
        self._salvar()
        return self.contexto()

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "presenca_maquina_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado_presenca": self._dados.get("estado_presenca"),
            "startup_id": self._dados.get("startup_id"),
            "iniciado_em": self._dados.get("iniciado_em"),
            "ultimo_heartbeat": self._dados.get("ultimo_heartbeat"),
            "encerrado_em": self._dados.get("encerrado_em"),
            "motivo_encerramento": self._dados.get(
                "motivo_encerramento"
            ),
            "retomada": copy.deepcopy(
                self._dados.get("retomada", {})
            ),
            "residencia": copy.deepcopy(
                self._dados.get("residencia", {})
            ),
            "historico_limitado": True,
            "arquivo_unico": True,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = ["PresencaMaquinaNixOS"]
