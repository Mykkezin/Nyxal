#!/usr/bin/env python3
"""NYXOS — M5.18 auditoria encadeada de atuação."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - compatibilidade fora de Unix
    fcntl = None


class AuditoriaAtuacaoNixOS:
    FONTE = "auditoria_atuacao_nyxos"
    VERSAO = "5.18.1"

    def __init__(self, *, arquivo: str | Path | None = None) -> None:
        self.arquivo = Path(arquivo) if arquivo is not None else None
        self._ultimo_hash = "GENESIS"
        self._sequencia = 0
        self._arquivo_recuperado: str | None = None
        self._carregar_estado()

    @property
    def _arquivo_lock(self) -> Path | None:
        if self.arquivo is None:
            return None
        return self.arquivo.with_name(self.arquivo.name + ".lock")

    @contextlib.contextmanager
    def _lock_exclusivo(self):
        if self._arquivo_lock is None:
            yield
            return

        self._arquivo_lock.parent.mkdir(parents=True, exist_ok=True)
        with self._arquivo_lock.open("a", encoding="utf-8") as lock:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def registrar(self, *, evento: str, dados: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(evento, str) or not evento:
            raise ValueError("evento_invalido")
        if not isinstance(dados, dict):
            raise TypeError("dados_invalidos")

        with self._lock_exclusivo():
            # Recarrega dentro da trava para que dois processos nunca
            # partam do mesmo sequencial/hash anterior.
            self._carregar_estado_sem_lock()
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
                "hash": hashlib.sha256(
                    canonico.encode("utf-8")
                ).hexdigest(),
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

        with self._lock_exclusivo():
            return self._validar_sem_lock()

    def _validar_sem_lock(self) -> dict[str, Any]:
        anterior = "GENESIS"
        quantidade = 0

        try:
            linhas = self.arquivo.read_text(
                encoding="utf-8"
            ).splitlines()
        except (OSError, UnicodeDecodeError) as erro:
            return {
                "valido": False,
                "registros": quantidade,
                "motivo": "leitura_auditoria_falhou",
                "detalhe": f"{type(erro).__name__}: {erro}",
            }

        for linha in linhas:
            if not linha.strip():
                continue

            try:
                registro = json.loads(linha)
            except json.JSONDecodeError:
                return {
                    "valido": False,
                    "registros": quantidade,
                    "motivo": "json_invalido",
                }

            if not isinstance(registro, dict):
                return {
                    "valido": False,
                    "registros": quantidade,
                    "motivo": "registro_invalido",
                }

            base = dict(registro)
            hash_registro = base.pop("hash", None)
            canonico = json.dumps(
                base,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            esperado = hashlib.sha256(
                canonico.encode("utf-8")
            ).hexdigest()

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
            "arquivo_recuperado": self._arquivo_recuperado,
            "validacao": self.validar(),
        }

    def _persistir(self, registro: dict[str, Any]) -> None:
        if self.arquivo is None:
            return

        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        linha = (
            json.dumps(
                registro,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )

        with self.arquivo.open("a", encoding="utf-8") as arquivo:
            arquivo.write(linha)
            arquivo.flush()
            os.fsync(arquivo.fileno())

    def _carregar_estado(self) -> None:
        if self.arquivo is None:
            return

        with self._lock_exclusivo():
            self._carregar_estado_sem_lock()

    def _carregar_estado_sem_lock(self) -> None:
        if self.arquivo is None or not self.arquivo.exists():
            return

        try:
            linhas = [
                linha
                for linha in self.arquivo.read_text(
                    encoding="utf-8"
                ).splitlines()
                if linha.strip()
            ]
        except (OSError, UnicodeDecodeError):
            self._preservar_arquivo_corrompido("leitura")
            return

        if not linhas:
            return

        anterior = "GENESIS"
        quantidade = 0

        for linha in linhas:
            try:
                registro = json.loads(linha)
            except json.JSONDecodeError:
                self._preservar_arquivo_corrompido("json")
                return

            if not isinstance(registro, dict):
                self._preservar_arquivo_corrompido("registro")
                return

            base = dict(registro)
            hash_registro = base.pop("hash", None)
            canonico = json.dumps(
                base,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            esperado = hashlib.sha256(
                canonico.encode("utf-8")
            ).hexdigest()

            if (
                hash_registro != esperado
                or registro.get("hash_anterior") != anterior
                or registro.get("sequencia") != quantidade + 1
            ):
                self._preservar_arquivo_corrompido("cadeia")
                return

            anterior = hash_registro
            quantidade += 1

        self._sequencia = quantidade
        self._ultimo_hash = anterior

    def _preservar_arquivo_corrompido(self, motivo: str) -> None:
        if self.arquivo is None or not self.arquivo.exists():
            return

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        destino = self.arquivo.with_name(
            f"{self.arquivo.name}.corrompido-{motivo}-{timestamp}-{os.getpid()}"
        )

        try:
            os.replace(self.arquivo, destino)
            self._arquivo_recuperado = str(destino)
        except OSError:
            # Falha ao preservar não deve impedir a inicialização; o próximo
            # registro ainda terá uma cadeia nova apenas se o arquivo puder
            # ser recriado.
            self._arquivo_recuperado = None

        self._sequencia = 0
        self._ultimo_hash = "GENESIS"


__all__ = ["AuditoriaAtuacaoNixOS"]
