#!/usr/bin/env python3

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nixal_fila_tarefas import FilaTarefasNixal

if TYPE_CHECKING:
    from nixal_agente_qwen import AgenteNixalQwen


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
        if agente is None:
            # Defer Ollama import until the real Qwen agent is requested.
            # The governed queue/executor can be imported and tested without a model runtime.
            from nixal_agente_qwen import AgenteNixalQwen

            self.agente = AgenteNixalQwen()
        else:
            self.agente = agente

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
        *,
        chave_idempotencia: str | None = None,
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
            chave_idempotencia=chave_idempotencia,
        )
        adicionada_estado = adicionada.get("estado")

        return {
            "sucesso": adicionada.get("sucesso") is True,
            "estado": (
                "tarefa_ja_existente"
                if adicionada.get("sucesso") is True and adicionada_estado == "ja_existente"
                else "tarefa_adicionada"
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
        *,
        chave_idempotencia: str | None = None,
    ) -> dict[str, Any]:
        recebida = self.receber_ordem(
            ordem,
            chave_idempotencia=chave_idempotencia,
        )
        if recebida.get("sucesso") is not True:
            return recebida

        valor_recebido = recebida.get("valor")
        tarefa = valor_recebido.get("tarefa") if isinstance(valor_recebido, dict) else None
        tarefa_id = tarefa.get("id") if isinstance(tarefa, dict) else None
        if not isinstance(tarefa_id, str) or not tarefa_id:
            return {
                "sucesso": False,
                "estado": "tarefa_enfileirada_sem_id",
                "origem": self.FONTE,
                "valor": {"ordem": ordem, "tarefa": tarefa},
                "motivo": "A fila aceitou a ordem sem devolver um ID de tarefa válido.",
            }

        if recebida.get("estado") == "tarefa_ja_existente":
            estado_existente = tarefa.get("estado") if isinstance(tarefa, dict) else None
            if estado_existente in {"concluida", "falhou", "negada", "resultado_indeterminado"}:
                resultado_existente = tarefa.get("resultado", {}) if isinstance(tarefa, dict) else {}
                sucesso_existente = (
                    estado_existente == "concluida"
                    and isinstance(resultado_existente, dict)
                    and resultado_existente.get("sucesso") is True
                )
                return {
                    "sucesso": sucesso_existente,
                    "estado": "tarefa_ja_existente",
                    "origem": self.FONTE,
                    "valor": {
                        "ordem": ordem,
                        "tarefa": tarefa,
                        "executada": False,
                        "idempotente": True,
                        "execucao": {
                            "sucesso": sucesso_existente,
                            "estado": estado_existente,
                            "valor": tarefa,
                        },
                    },
                }

        # A resposta precisa se referir à ordem recebida. Nunca consuma silenciosamente
        # uma tarefa anterior e devolva o resultado como se fosse desta ordem.
        execucao = self.fila.executar_proxima(tarefa_id_esperado=tarefa_id)
        estado_execucao = execucao.get("estado")
        if estado_execucao == "tarefa_aguarda_ordem":
            return {
                "sucesso": True,
                "estado": "tarefa_enfileirada_aguardando_ordem",
                "origem": self.FONTE,
                "valor": {
                    "ordem": ordem,
                    "tarefa": tarefa,
                    "executada": False,
                    "execucao": execucao,
                },
                "motivo": "A ordem foi persistida e aguardará as tarefas anteriores na fila.",
            }
        if estado_execucao == "tarefa_em_execucao":
            return {
                "sucesso": True,
                "estado": "tarefa_enfileirada_aguardando_execucao_anterior",
                "origem": self.FONTE,
                "valor": {
                    "ordem": ordem,
                    "tarefa": tarefa,
                    "executada": False,
                    "execucao": execucao,
                },
                "motivo": "A ordem foi persistida; outra tarefa ainda está em execução.",
            }

        return {
            "sucesso": execucao.get("sucesso") is True,
            "estado": estado_execucao,
            "origem": self.FONTE,
            "valor": {
                "ordem": ordem,
                "tarefa": tarefa,
                "executada": estado_execucao in {"concluida", "falhou", "negada"},
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
