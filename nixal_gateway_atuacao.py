#!/usr/bin/env python3
"""NYXOS — M5.15 gateway governado de atuação.

Recebe um plano central, valida a ação contra uma allowlist e separa
planejamento, autorização e execução. Por padrão, a atuação física permanece
desabilitada e nenhum comando do host é executado.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from nixal_auditoria_atuacao import AuditoriaAtuacaoNixOS


class GatewayAtuacaoNixOS:
    FONTE = "gateway_atuacao_nyxos"
    VERSAO = "5.15.0"

    ACOES_PERMITIDAS = {
        "observar",
        "aguardar",
        "reduzir_carga",
        "preservar_estado",
        "preparar_gateway",
    }

    def __init__(
        self,
        *,
        arquivo: str | Path | None = None,
        executor: Callable[[str], dict[str, Any]] | None = None,
        execucao_fisica_habilitada: bool = False,
        auditoria: AuditoriaAtuacaoNixOS | None = None,
    ) -> None:
        self.arquivo = Path(arquivo) if arquivo is not None else None
        self.executor = executor
        self.execucao_fisica_habilitada = bool(execucao_fisica_habilitada)
        self._ultimo_gateway: dict[str, Any] | None = None
        self.auditoria = auditoria

    @staticmethod
    def _id_operacao(plano_id: str, acao: str) -> str:
        base = f"{plano_id}:{acao}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def preparar(
        self,
        *,
        plano: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(plano, dict):
            raise TypeError("plano_invalido")

        plano_id = plano.get("plano_id")
        decisao = plano.get("decisao")
        acao = decisao.get("acao_planejada") if isinstance(decisao, dict) else None

        if not isinstance(plano_id, str) or not plano_id:
            raise ValueError("plano_id_invalido")
        if acao not in self.ACOES_PERMITIDAS:
            raise ValueError("acao_nao_permitida")

        operacao = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "plano_id": plano_id,
            "operacao_id": self._id_operacao(plano_id, acao),
            "acao": acao,
            "estado": "preparada",
            "autorizacao_explicita": False,
            "execucao_fisica_habilitada": self.execucao_fisica_habilitada,
            "executada": False,
            "executor_disponivel": self.executor is not None,
            "gateway_atuacao": True,
            "governanca": {
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }

        self._ultimo_gateway = copy.deepcopy(operacao)
        self._auditar("operacao_preparada", operacao)
        self._persistir()
        return copy.deepcopy(operacao)

    def executar(
        self,
        *,
        operacao: dict[str, Any],
        autorizacao_explicita: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(operacao, dict):
            raise TypeError("operacao_invalida")

        acao = operacao.get("acao")
        if acao not in self.ACOES_PERMITIDAS:
            raise ValueError("acao_nao_permitida")

        if autorizacao_explicita is not True:
            return self._resultado_bloqueado(
                operacao,
                "autorizacao_explicita_ausente",
            )

        if not self.execucao_fisica_habilitada:
            return self._resultado_bloqueado(
                operacao,
                "execucao_fisica_desabilitada",
            )

        if self.executor is None:
            return self._resultado_bloqueado(
                operacao,
                "executor_nao_configurado",
            )

        resultado = self.executor(acao)
        if not isinstance(resultado, dict):
            raise TypeError("executor_precisa_retornar_dict")

        saida = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "executado",
            "plano_id": operacao.get("plano_id"),
            "operacao_id": operacao.get("operacao_id"),
            "acao": acao,
            "autorizacao_explicita": True,
            "execucao_fisica_habilitada": True,
            "executada": True,
            "resultado_executor": copy.deepcopy(resultado),
            "governanca": {
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }
        self._ultimo_gateway = copy.deepcopy(saida)
        self._auditar("operacao_executada", saida)
        self._persistir()
        return copy.deepcopy(saida)

    def _resultado_bloqueado(
        self,
        operacao: dict[str, Any],
        motivo: str,
    ) -> dict[str, Any]:
        saida = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "bloqueado",
            "plano_id": operacao.get("plano_id"),
            "operacao_id": operacao.get("operacao_id"),
            "acao": operacao.get("acao"),
            "motivo": motivo,
            "autorizacao_explicita": False,
            "execucao_fisica_habilitada": self.execucao_fisica_habilitada,
            "executada": False,
            "governanca": {
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }
        self._ultimo_gateway = copy.deepcopy(saida)
        self._auditar("operacao_bloqueada", saida)
        self._persistir()
        return copy.deepcopy(saida)

    def _auditar(self, evento: str, dados: dict[str, Any]) -> None:
        if self.auditoria is not None:
            self.auditoria.registrar(evento=evento, dados=dados)

    def _persistir(self) -> None:
        if self.arquivo is None or self._ultimo_gateway is None:
            return
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo.write_text(
            json.dumps(
                self._ultimo_gateway,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "gateway_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "ultimo_gateway": copy.deepcopy(self._ultimo_gateway),
            "acoes_permitidas": sorted(self.ACOES_PERMITIDAS),
            "execucao_fisica_habilitada": self.execucao_fisica_habilitada,
            "executor_configurado": self.executor is not None,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = ["GatewayAtuacaoNixOS"]
