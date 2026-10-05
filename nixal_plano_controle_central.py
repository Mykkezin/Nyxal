#!/usr/bin/env python3
"""NYXOS — M5.14 plano central de controle."""

from __future__ import annotations

import copy
from typing import Any

from nixal_agente_qwen import AgenteNixalQwen
from nixal_fisiologia_operacional import FisiologiaOperacionalNixOS
from nixal_gateway_atuacao_host import GatewayAtuacaoHostNixOS
from nixal_habitat import HabitatNixOS


class PlanoControleCentralNixOS:
    """Superfície central de orquestração sem executor próprio."""

    FONTE = "plano_controle_central_nyxos"
    VERSAO = "5.14.0"

    OPERACOES_VALIDAS = {
        "observar",
        "selecionar_capacidade",
        "atuar_host",
    }

    def __init__(
        self,
        *,
        habitat: HabitatNixOS | None = None,
        fisiologia: FisiologiaOperacionalNixOS | None = None,
        gateway_host: GatewayAtuacaoHostNixOS | None = None,
        agente: AgenteNixalQwen | None = None,
    ) -> None:
        self.habitat = habitat or HabitatNixOS()
        self.fisiologia = fisiologia
        self.gateway_host = gateway_host
        self.agente = agente

    def observar(self) -> dict[str, Any]:
        habitat = self.habitat.snapshot()
        fisiologia = (
            self.fisiologia.contexto()
            if self.fisiologia is not None
            else None
        )
        gateway = (
            self.gateway_host.contexto()
            if self.gateway_host is not None
            else None
        )

        return self._resposta(
            True,
            "observacao_centralizada",
            {
                "habitat": copy.deepcopy(habitat),
                "fisiologia": copy.deepcopy(fisiologia),
                "gateway_atuacao": copy.deepcopy(gateway),
            },
        )

    def selecionar_capacidade(
        self,
        necessidade: str,
    ) -> dict[str, Any]:
        if not isinstance(necessidade, str) or not necessidade.strip():
            return self._resposta(
                False,
                "necessidade_invalida",
                {"motivo": "A necessidade precisa ser texto."},
            )

        if self.agente is None:
            return self._resposta(
                False,
                "agente_sem_configuracao",
                {"motivo": "O agente semântico não foi configurado."},
            )

        selecao = self.agente.selecionar_capacidade(
            necessidade
        )

        return self._resposta(
            bool(selecao.get("sucesso") is True),
            "capacidade_selecionada" if selecao.get("sucesso") else "selecao_falhou",
            {"necessidade": necessidade, "selecao": copy.deepcopy(selecao)},
        )

    def atuar_host(
        self,
        solicitacao: Any,
        *,
        autorizacao_acao: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if self.gateway_host is None:
            return self._resposta(
                False,
                "gateway_atuacao_indisponivel",
                {"motivo": "O gateway de atuação não foi configurado."},
            )

        resultado = self.gateway_host.executar(
            solicitacao,
            autorizacao_acao=autorizacao_acao,
            dry_run=dry_run,
        )

        return self._resposta(
            bool(resultado.get("sucesso") is True),
            resultado.get("estado", "atuacao_processada"),
            {"resultado": copy.deepcopy(resultado)},
        )

    def processar(
        self,
        operacao: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(operacao, str) or not operacao.strip():
            return self._resposta(
                False,
                "operacao_invalida",
                {"motivo": "A operação precisa possuir nome."},
            )

        operacao = operacao.strip()
        if operacao not in self.OPERACOES_VALIDAS:
            return self._resposta(
                False,
                "operacao_nao_permitida",
                {"operacao": operacao},
            )

        payload = {} if payload is None else payload
        if not isinstance(payload, dict):
            return self._resposta(
                False,
                "payload_invalido",
                {"motivo": "O payload precisa ser objeto."},
            )

        if operacao == "observar":
            return self.observar()

        if operacao == "selecionar_capacidade":
            return self.selecionar_capacidade(
                payload.get("necessidade", "")
            )

        if operacao == "atuar_host":
            return self.atuar_host(
                payload.get("solicitacao"),
                autorizacao_acao=payload.get(
                    "autorizacao_acao", False
                ),
                dry_run=payload.get(
                    "dry_run", False
                ),
            )

        raise AssertionError(
            "operação validada não possui roteamento"
        )

    @staticmethod
    def _resposta(
        sucesso: bool,
        estado: str,
        valor: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "sucesso": sucesso,
            "estado": estado,
            "origem": PlanoControleCentralNixOS.FONTE,
            "versao": PlanoControleCentralNixOS.VERSAO,
            "valor": valor,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "plano_controle_central_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "operacoes": sorted(self.OPERACOES_VALIDAS),
            "possui_agente_semantico": self.agente is not None,
            "possui_gateway_atuacao": self.gateway_host is not None,
            "possui_fisiologia": self.fisiologia is not None,
            "executor_proprio": False,
            "shell_arbitrario": False,
            "autorizacao_evolucao": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = ["PlanoControleCentralNixOS"]
