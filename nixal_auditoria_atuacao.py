#!/usr/bin/env python3
"""NYXOS — M5.18 auditoria encadeada de atuação."""

from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Any


class AuditoriaAtuacaoNixOS:
    FONTE = "auditoria_atuacao_nyxos"
    VERSAO = "5.18.0"

    def __init__(self, *, arquivo: str | Path | None = None) -> None:
        self.arquivo = Path(arquivo) if arquivo is not None else None
        self._ultimo_hash = "GENESIS"
        self._sequencia = 0
        self._carregar_estado()

    def registrar(self, *, evento: str, dados: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(evento, str) or not evento:
            raise ValueError("evento_invalido")
        if not isinstance(dados, dict):
            raise TypeError("dados_invalidos")

        self._sequencia += 1
        registro_base = {
            "fonte": self.FONTE,
            "versao": self.VERSAO,
            "sequencia": self._sequencia,
            "timestamp_epoch_ns": time.time_ns(),
            "evento": evento,
            "dados": copy.deepcopy(dados),
            "hash_anterior": self._ultimo_hash,
        }
        canonico = json.dumps(
            registro_base,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        registro = {
            **registro_base,
            "hash": hashlib.sha256(canonico.encode("utf-8")).hexdigest(),
        }
        self._ultimo_hash = registro["hash"]
        self._persistir(registro)
        return copy.deepcopy(registro)

    def validar(self) -> dict[str, Any]:
        if self.arquivo is None or not self.arquivo.exists():
            return {
                "valido": True,
                "registros": 0,
                "ultimo_hash": self._ultimo_hash,
            }

        anterior = "GENESIS"
        quantidade = 0
        for linha in self.arquivo.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            registro = json.loads(linha)
            base = dict(registro)
            hash_registro = base.pop("hash", None)
            canonico = json.dumps(
                base,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            esperado = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
            if (
                hash_registro != esperado
                or registro.get("hash_anterior") != anterior
                or registro.get("sequencia") != quantidade + 1
            ):
                return {
                    "valido": False,
                    "registros": quantidade,
                    "motivo": "cadeia_de_auditoria_invalida",
                }
            anterior = hash_registro
            quantidade += 1

        return {
            "valido": True,
            "registros": quantidade,
            "ultimo_hash": anterior,
        }

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "auditoria_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "arquivo": str(self.arquivo) if self.arquivo else None,
            "sequencia": self._sequencia,
            "ultimo_hash": self._ultimo_hash,
            "validacao": self.validar(),
        }

    def _persistir(self, registro: dict[str, Any]) -> None:
        if self.arquivo is None:
            return
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        with self.arquivo.open("a", encoding="utf-8") as arquivo:
            arquivo.write(
                json.dumps(
                    registro,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    def _carregar_estado(self) -> None:
        if self.arquivo is None or not self.arquivo.exists():
            return
        linhas = [
            linha for linha in
            self.arquivo.read_text(encoding="utf-8").splitlines()
            if linha.strip()
        ]
        if not linhas:
            return
        ultimo = json.loads(linhas[-1])
        self._sequencia = int(ultimo["sequencia"])
        self._ultimo_hash = str(ultimo["hash"])


__all__ = ["AuditoriaAtuacaoNixOS"]
