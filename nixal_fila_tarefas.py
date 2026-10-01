#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from nixal_capacidades import GerenciadorCapacidades


ARQUIVO_FILA_PADRAO = (
    Path(__file__).resolve().parent
    / "fila_tarefas_nixal.json"
)

VERSAO_FILA = "1.0"


class FilaTarefasNixal:
    """Fila persistente de tarefas autorizadas da Nyxal."""

    FONTE = "fila_tarefas_nixal"

    def __init__(
        self,
        caminho: Path = ARQUIVO_FILA_PADRAO,
        capacidades: GerenciadorCapacidades | None = None,
    ) -> None:
        self.caminho = Path(caminho)
        self.capacidades = (
            capacidades
            if capacidades is not None
            else GerenciadorCapacidades()
        )
        self._dados = self._carregar()

    def _estrutura_vazia(self) -> dict[str, Any]:
        return {
            "versao": VERSAO_FILA,
            "tarefas": [],
        }

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho.exists():
            return self._estrutura_vazia()

        try:
            dados = json.loads(
                self.caminho.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return self._estrutura_vazia()

        if (
            not isinstance(dados, dict)
            or dados.get("versao") != VERSAO_FILA
            or not isinstance(dados.get("tarefas"), list)
        ):
            return self._estrutura_vazia()

        return copy.deepcopy(dados)

    def _salvar(self) -> None:
        self.caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporario = self.caminho.with_suffix(
            self.caminho.suffix + ".tmp"
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
            self.caminho,
        )

    @staticmethod
    def _id_tarefa(
        capacidade: str,
        argumentos: dict[str, Any],
    ) -> str:
        base = json.dumps(
            {
                "capacidade": capacidade,
                "argumentos": argumentos,
                "tempo": time.time_ns(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            base.encode("utf-8")
        ).hexdigest()

    def adicionar(
        self,
        capacidade: str,
        argumentos: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(capacidade, str) or not capacidade.strip():
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": self.FONTE,
                "motivo": "Nome da capacidade inválido.",
            }

        if argumentos is None:
            argumentos = {}

        if not isinstance(argumentos, dict):
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": self.FONTE,
                "motivo": "Argumentos precisam ser um objeto.",
            }

        tarefa = {
            "id": self._id_tarefa(
                capacidade,
                argumentos,
            ),
            "capacidade": capacidade,
            "argumentos": copy.deepcopy(argumentos),
            "estado": "pendente",
            "criado_em": time.time(),
            "resultado": None,
            "erro": None,
        }

        self._dados["tarefas"].append(tarefa)
        self._salvar()

        return {
            "sucesso": True,
            "estado": "pendente",
            "origem": self.FONTE,
            "valor": copy.deepcopy(tarefa),
        }

    def executar_proxima(self) -> dict[str, Any]:
        for tarefa in self._dados["tarefas"]:
            if tarefa.get("estado") != "pendente":
                continue

            tarefa["estado"] = "executando"
            self._salvar()

            try:
                resultado = self.capacidades.executar(
                    tarefa["capacidade"],
                    **tarefa["argumentos"],
                )

                if resultado.sucesso:
                    tarefa["estado"] = "concluida"
                    tarefa["resultado"] = {
                        "sucesso": True,
                        "capacidade": resultado.capacidade,
                        "resultado": resultado.resultado,
                        "timestamp": resultado.timestamp,
                        "duracao_ms": resultado.duracao_ms,
                    }
                    tarefa["erro"] = None
                else:
                    tarefa["estado"] = "falhou"
                    tarefa["resultado"] = {
                        "sucesso": False,
                        "capacidade": resultado.capacidade,
                        "resultado": resultado.resultado,
                        "timestamp": resultado.timestamp,
                        "duracao_ms": resultado.duracao_ms,
                    }
                    tarefa["erro"] = resultado.erro

            except Exception as erro:
                tarefa["estado"] = "falhou"
                tarefa["erro"] = (
                    f"{type(erro).__name__}: {erro}"
                )

            self._salvar()

            return {
                "sucesso": tarefa["estado"] == "concluida",
                "estado": tarefa["estado"],
                "origem": self.FONTE,
                "valor": copy.deepcopy(tarefa),
            }

        return {
            "sucesso": True,
            "estado": "fila_vazia",
            "origem": self.FONTE,
            "valor": None,
        }

    def listar(self) -> list[dict[str, Any]]:
        return copy.deepcopy(
            self._dados.get("tarefas", [])
        )

    def quantidade(self) -> int:
        return len(
            self._dados.get("tarefas", [])
        )

    def quantidade_pendentes(self) -> int:
        return sum(
            1
            for tarefa in self._dados.get("tarefas", [])
            if tarefa.get("estado") == "pendente"
        )

    def recarregar(self) -> dict[str, Any]:
        self._dados = self._carregar()

        return {
            "sucesso": True,
            "estado": "recarregado",
            "origem": self.FONTE,
            "valor": {
                "quantidade": self.quantidade(),
                "pendentes": self.quantidade_pendentes(),
            },
        }


if __name__ == "__main__":
    fila = FilaTarefasNixal()

    print("=" * 60)
    print("NIXAL — FILA DE TAREFAS")
    print("=" * 60)
    print(
        json.dumps(
            fila.recarregar(),
            ensure_ascii=False,
            indent=2,
        )
    )
