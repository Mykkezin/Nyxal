#!/usr/bin/env python3

from __future__ import annotations

from typing import Any

from nixal_agente_qwen import AgenteNixalQwen
from nixal_fila_tarefas import FilaTarefasNixal


class ExecutorOrdensNixal:
    """
    Ponte entre uma ordem em linguagem natural,
    o agente Qwen e a fila persistente de tarefas.
    """

    FONTE = "executor_ordens_nixal"
    VERSAO = "1.0"

    def __init__(
        self,
        agente: AgenteNixalQwen | None = None,
        fila: FilaTarefasNixal | None = None,
    ) -> None:
        self.agente = (
            agente
            if agente is not None
            else AgenteNixalQwen()
        )

        self.fila = (
            fila
            if fila is not None
            else FilaTarefasNixal(
                capacidades=self.agente.capacidades
            )
        )

    def receber_ordem(
        self,
        ordem: str,
    ) -> dict[str, Any]:
        if not isinstance(ordem, str) or not ordem.strip():
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": self.FONTE,
                "motivo": "A ordem precisa ser um texto.",
            }

        selecao = self.agente.selecionar_capacidade(
            ordem
        )

        if not selecao.get("sucesso"):
            return {
                "sucesso": False,
                "estado": "selecao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "ordem": ordem,
                    "selecao": selecao,
                },
                "motivo": selecao.get(
                    "erro",
                    "A seleção da capacidade falhou.",
                ),
            }

        capacidade = selecao.get("capacidade")
        argumentos = selecao.get(
            "argumentos",
            {},
        )

        if not capacidade:
            return {
                "sucesso": False,
                "estado": "nenhuma_capacidade",
                "origem": self.FONTE,
                "valor": {
                    "ordem": ordem,
                    "selecao": selecao,
                },
                "motivo": selecao.get(
                    "motivo",
                    "Nenhuma capacidade foi selecionada.",
                ),
            }

        adicionada = self.fila.adicionar(
            capacidade=capacidade,
            argumentos=argumentos,
        )

        return {
            "sucesso": adicionada.get("sucesso") is True,
            "estado": (
                "tarefa_adicionada"
                if adicionada.get("sucesso") is True
                else "fila_rejeitou_tarefa"
            ),
            "origem": self.FONTE,
            "valor": {
                "ordem": ordem,
                "capacidade": capacidade,
                "argumentos": argumentos,
                "selecao": selecao,
                "tarefa": adicionada.get("valor"),
            },
            "motivo": adicionada.get("motivo"),
        }

    def executar_proxima(self) -> dict[str, Any]:
        return self.fila.executar_proxima()

    def atender(
        self,
        ordem: str,
    ) -> dict[str, Any]:
        recebida = self.receber_ordem(
            ordem
        )

        if not recebida.get("sucesso"):
            return recebida

        execucao = self.executar_proxima()

        return {
            "sucesso": execucao.get("sucesso") is True,
            "estado": execucao.get("estado"),
            "origem": self.FONTE,
            "valor": {
                "ordem": ordem,
                "tarefa": recebida.get(
                    "valor",
                    {},
                ).get("tarefa"),
                "execucao": execucao,
            },
        }

    def listar_pendentes(self) -> list[dict[str, Any]]:
        return [
            tarefa
            for tarefa in self.fila.listar()
            if tarefa.get("estado") == "pendente"
        ]


if __name__ == "__main__":
    executor = ExecutorOrdensNixal()

    print("=" * 60)
    print("NIXAL — EXECUTOR DE ORDENS")
    print("=" * 60)
    print("Pendentes:", len(executor.listar_pendentes()))
