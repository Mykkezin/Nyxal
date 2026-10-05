#!/usr/bin/env python3
"""NYXOS — M5.17 sandbox físico reversível.

Implementa a primeira mutação física real, porém confinada a um diretório
sandbox explicitamente configurado. A capacidade física permanece desligada
por padrão e toda mutação suportada possui rollback.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


class AdaptadorSandboxFisicoNixOS:
    FONTE = "adaptador_sandbox_fisico_nyxos"
    VERSAO = "5.17.0"

    ACOES_SOMENTE_LEITURA = {
        "observar",
        "aguardar",
        "preparar_gateway",
    }
    ACOES_FISICAS = {
        "preservar_estado",
    }
    ACOES_FISICAS_BLOQUEADAS = {
        "reduzir_carga",
    }

    def __init__(
        self,
        *,
        diretorio_sandbox: str | Path,
        habilitada: bool = False,
    ) -> None:
        self.diretorio_sandbox = Path(diretorio_sandbox).resolve()
        self.habilitada = bool(habilitada)
        self.diretorio_sandbox.mkdir(parents=True, exist_ok=True)
        self._ultimo_resultado: dict[str, Any] | None = None

    def executar(self, acao: str) -> dict[str, Any]:
        if acao not in (
            self.ACOES_SOMENTE_LEITURA
            | self.ACOES_FISICAS
            | self.ACOES_FISICAS_BLOQUEADAS
        ):
            raise ValueError("acao_nao_conhecida")

        if acao in self.ACOES_FISICAS_BLOQUEADAS:
            return self._bloquear(
                acao,
                "atuacao_fisica_nao_implementada",
            )

        if acao in self.ACOES_FISICAS and not self.habilitada:
            return self._bloquear(
                acao,
                "sandbox_fisico_desabilitado",
            )

        if acao == "preservar_estado":
            return self._preservar_estado()

        resultado = {
            "operacao": acao,
            "efeito_fisico": False,
        }
        saida = self._resultado_executado(
            acao=acao,
            resultado=resultado,
            atuacao_fisica=False,
            mutacao_host=False,
        )
        return saida

    def _preservar_estado(self) -> dict[str, Any]:
        instante = time.time_ns()
        nome = f"estado-{os.getpid()}-{instante}.json"
        alvo = (self.diretorio_sandbox / nome).resolve()

        if not self._dentro_do_sandbox(alvo):
            return self._bloquear(
                "preservar_estado",
                "alvo_fora_do_sandbox",
            )

        payload = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "pid": os.getpid(),
            "timestamp_epoch_ns": instante,
            "estado": "preservado",
        }
        texto = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        alvo.write_text(texto, encoding="utf-8")

        token = hashlib.sha256(
            str(alvo).encode("utf-8")
        ).hexdigest()

        return self._resultado_executado(
            acao="preservar_estado",
            resultado={
                "arquivo": str(alvo),
                "rollback_token": token,
                "bytes": len(texto.encode("utf-8")),
            },
            atuacao_fisica=True,
            mutacao_host=True,
        )

    def rollback(self, rollback_token: str) -> dict[str, Any]:
        if not isinstance(rollback_token, str) or not rollback_token:
            raise ValueError("rollback_token_invalido")

        for alvo in self.diretorio_sandbox.glob("estado-*.json"):
            token = hashlib.sha256(
                str(alvo.resolve()).encode("utf-8")
            ).hexdigest()
            if token != rollback_token:
                continue

            alvo_resolvido = alvo.resolve()
            if not self._dentro_do_sandbox(alvo_resolvido):
                return {
                    "sucesso": False,
                    "estado": "bloqueado",
                    "motivo": "alvo_fora_do_sandbox",
                    "rollback_executado": False,
                }

            alvo_resolvido.unlink()
            return {
                "sucesso": True,
                "estado": "rollback_executado",
                "rollback_executado": True,
                "arquivo": str(alvo_resolvido),
                "atuacao_fisica": True,
                "mutacao_host": True,
            }

        return {
            "sucesso": False,
            "estado": "nao_encontrado",
            "motivo": "rollback_token_nao_localizado",
            "rollback_executado": False,
        }

    def _resultado_executado(
        self,
        *,
        acao: str,
        resultado: dict[str, Any],
        atuacao_fisica: bool,
        mutacao_host: bool,
    ) -> dict[str, Any]:
        saida = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "executado_controlado",
            "acao": acao,
            "executada": True,
            "atuacao_fisica": atuacao_fisica,
            "mutacao_host": mutacao_host,
            "sandbox": str(self.diretorio_sandbox),
            "resultado": copy.deepcopy(resultado),
            "governanca": {
                "autorizacao_explicita": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }
        self._ultimo_resultado = copy.deepcopy(saida)
        return copy.deepcopy(saida)

    def _bloquear(self, acao: str, motivo: str) -> dict[str, Any]:
        saida = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "bloqueado",
            "acao": acao,
            "motivo": motivo,
            "executada": False,
            "atuacao_fisica": False,
            "mutacao_host": False,
            "sandbox": str(self.diretorio_sandbox),
            "governanca": {
                "autorizacao_explicita": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }
        self._ultimo_resultado = copy.deepcopy(saida)
        return copy.deepcopy(saida)

    def _dentro_do_sandbox(self, alvo: Path) -> bool:
        try:
            alvo.relative_to(self.diretorio_sandbox)
            return True
        except ValueError:
            return False

    def __call__(self, acao: str) -> dict[str, Any]:
        return self.executar(acao)

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "sandbox_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "diretorio_sandbox": str(self.diretorio_sandbox),
            "habilitada": self.habilitada,
            "acoes_somente_leitura": sorted(self.ACOES_SOMENTE_LEITURA),
            "acoes_fisicas": sorted(self.ACOES_FISICAS),
            "acoes_fisicas_bloqueadas": sorted(
                self.ACOES_FISICAS_BLOQUEADAS
            ),
            "rollback_disponivel": True,
            "ultimo_resultado": copy.deepcopy(self._ultimo_resultado),
        }


__all__ = ["AdaptadorSandboxFisicoNixOS"]
