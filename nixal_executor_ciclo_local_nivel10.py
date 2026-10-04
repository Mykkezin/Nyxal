#!/usr/bin/env python3
"""
NYXAL — EXECUTOR DO CICLO LOCAL / NÍVEL 10

Integra o observador formal, a máquina de estados e o coordenador de
desenvolvimento já existente.

O executor:
    1. observa a branch;
    2. abre o ciclo formal quando há alteração;
    3. verifica branch/alvo e árvore limpa;
    4. registra a sincronização/preparação para o commit exato observado;
    5. executa apenas as validações previstas pelo coordenador;
    6. registra e classifica o resultado.

Limites:
- não faz fetch/pull automaticamente;
- não altera refs Git;
- não faz merge;
- não toca stable;
- não concede autorização;
- não executa candidatos externos;
- somente chama as rotinas de validação do coordenador.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from nixal_ciclo_local_nivel10 import (
    CicloLocalNivel10Nixal,
)
from nixal_coordenador_desenvolvimento import (
    CoordenadorDesenvolvimentoNixal,
)
from nixal_observador_desenvolvimento import (
    ObservadorDesenvolvimentoNixal,
)


class ExecutorCicloLocalNivel10Nixal:
    VERSAO = "10.3.0"
    FONTE = "executor_ciclo_local_nivel10_nixal"

    def __init__(
        self,
        *,
        repositorio: str | Path,
        branch: str = "desenvolvimento/mcp-bridge",
        estado_observador: str | Path | None = None,
        diretorio_registros: str | Path | None = None,
        observador: ObservadorDesenvolvimentoNixal | None = None,
        ciclo: CicloLocalNivel10Nixal | None = None,
        coordenador: Any | None = None,
    ) -> None:
        self.repositorio = Path(repositorio).resolve()
        self.branch = branch

        self.observador = observador or (
            ObservadorDesenvolvimentoNixal(
                repositorio=self.repositorio,
                branch=self.branch,
                estado_path=estado_observador,
            )
        )

        if diretorio_registros is None:
            diretorio_registros = (
                self.repositorio.parent
                / "Nyxal-reports"
                / "nivel10"
                / "ciclos"
            )

        self.ciclo = ciclo or (
            CicloLocalNivel10Nixal(
                diretorio_registros=diretorio_registros,
            )
        )

        self.coordenador = coordenador or (
            CoordenadorDesenvolvimentoNixal(
                repositorio=self.repositorio,
                branch=self.branch,
            )
        )

    @staticmethod
    def _resultado_precondicao(
        observacao: dict[str, Any],
        *,
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "versao": ExecutorCicloLocalNivel10Nixal.VERSAO,
            "fonte": ExecutorCicloLocalNivel10Nixal.FONTE,
            "estado": "bloqueado",
            "alteracao_detectada": (
                observacao.get(
                    "alteracao_detectada"
                )
                is True
            ),
            "motivo": motivo,
            "ciclo": copy.deepcopy(
                observacao.get("ciclo")
            ),
        }

    def executar(self) -> dict[str, Any]:
        # Pré-condições são verificadas antes da observação para que uma
        # árvore suja/branch incorreta não consuma o checkpoint observado.
        estado_git = self.coordenador.estado()

        if (
            estado_git.get("branch_atual")
            != self.branch
        ):
            return {
                "versao": self.VERSAO,
                "fonte": self.FONTE,
                "estado": "bloqueado",
                "alteracao_detectada": False,
                "motivo": "branch_incorreta",
                "observacao": None,
                "ciclo": None,
            }

        if not estado_git.get("arvore_limpa"):
            return {
                "versao": self.VERSAO,
                "fonte": self.FONTE,
                "estado": "bloqueado",
                "alteracao_detectada": False,
                "motivo": "arvore_de_trabalho_suja",
                "observacao": None,
                "ciclo": None,
            }

        observacao = self.observador.observar()

        if not observacao["alteracao_detectada"]:
            return {
                "versao": self.VERSAO,
                "fonte": self.FONTE,
                "estado": "sem_alteracao",
                "alteracao_detectada": False,
                "observacao": observacao,
                "ciclo": None,
            }

        registro = self.ciclo.abrir_ciclo(
            observacao
        )
        ciclo_id = registro["ciclo_id"]

        commit_atual = self.coordenador._git(
            "rev-parse",
            "--verify",
            f"refs/heads/{self.branch}",
        )

        if commit_atual != registro[
            "commit_novo"
        ]:
            return self._resultado_precondicao(
                observacao,
                motivo="commit_mudou_antes_da_validacao",
            )

        preparado = (
            self.ciclo.registrar_sincronizacao_preparada(
                ciclo_id,
                commit_validado=commit_atual,
                evidencias=[
                    "branch_correta",
                    "arvore_limpa",
                    "commit_confirmado",
                ],
            )
        )

        self.ciclo.iniciar_validacao(
            ciclo_id
        )

        validacao: dict[str, Any] = {}
        testes: dict[str, Any] = {}
        erro_tecnico: str | None = None

        try:
            validacao = (
                self.coordenador.validar_python_alterado()
            )
            if validacao.get("sucesso"):
                testes = (
                    self.coordenador.executar_testes_alterados()
                )
            else:
                testes = {
                    "sucesso": False,
                    "estado": "nao_executado",
                    "motivo": "validacao_python_reprovada",
                }
        except Exception as erro:
            erro_tecnico = f"{type(erro).__name__}: {erro}"
            validacao = {
                "sucesso": False,
                "estado": "erro_tecnico",
            }
            testes = {
                "sucesso": False,
                "estado": "nao_executado",
            }

        sucesso = bool(
            validacao.get("sucesso")
            and testes.get("sucesso")
            and erro_tecnico is None
        )

        diagnostico = (
            ""
            if sucesso
            else (
                erro_tecnico
                or (
                    "falha_em_validacao"
                    if not validacao.get("sucesso")
                    else "falha_em_testes"
                )
            )
        )

        concluido = (
            self.ciclo.concluir_validacao(
                ciclo_id,
                sucesso=sucesso,
                validacoes=[
                    {
                        "nome": "validacao_python_alterado",
                        "resultado": validacao,
                    },
                    {
                        "nome": "testes_python_alterados",
                        "resultado": testes,
                    },
                ],
                diagnostico=diagnostico,
            )
        )

        final = self.ciclo.classificar_resultado(
            ciclo_id
        )

        return {
            "versao": self.VERSAO,
            "fonte": self.FONTE,
            "estado": final["estado"],
            "alteracao_detectada": True,
            "observacao": observacao,
            "ciclo": final,
            "preparacao": preparado,
            "validacao": validacao,
            "testes": testes,
            "commit_validado": commit_atual,
        }


if __name__ == "__main__":
    print("ExecutorCicloLocalNivel10Nixal OK")
