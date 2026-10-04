#!/usr/bin/env python3
"""Teste determinístico do executor do ciclo local Nível 10."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_ciclo_local_nivel10 import (
    CicloLocalNivel10Nixal,
)
from nixal_executor_ciclo_local_nivel10 import (
    ExecutorCicloLocalNivel10Nixal,
)


class ObservadorFalso:
    def __init__(
        self,
        alteracao_detectada: bool,
    ) -> None:
        self.alteracao_detectada = (
            alteracao_detectada
        )

    def observar(self) -> dict:
        if not self.alteracao_detectada:
            return {
                "alteracao_detectada": False,
                "ciclo": None,
            }

        return {
            "alteracao_detectada": True,
            "ciclo": {
                "ciclo_id": CicloLocalNivel10Nixal._ciclo_id(
                    branch="desenvolvimento",
                    commit_anterior="1" * 40,
                    commit_novo="2" * 40,
                ),
                "branch": "desenvolvimento",
                "commit_anterior": "1" * 40,
                "commit_novo": "2" * 40,
                "estado": "alteracao_detectada",
            },
        }


class CoordenadorFalhaTecnica(CoordenadorFalso):
    def validar_python_alterado(self) -> dict:
        raise RuntimeError("falha_tecnica_teste")


class CoordenadorFalso:
    def __init__(self) -> None:
        self.validacoes = 0
        self.testes = 0

    def estado(self) -> dict:
        return {
            "branch_atual": "desenvolvimento",
            "arvore_limpa": True,
        }

    def _git(self, *args: str) -> str:
        assert args == (
            "rev-parse",
            "--verify",
            "refs/heads/desenvolvimento",
        )
        return "2" * 40

    def validar_python_alterado(self) -> dict:
        self.validacoes += 1
        return {
            "sucesso": True,
            "arquivos_python": [],
        }

    def executar_testes_alterados(self) -> dict:
        self.testes += 1
        return {
            "sucesso": True,
            "testes_python": [],
        }


def executar() -> None:
    with TemporaryDirectory() as temporario:
        raiz = Path(temporario)
        registros = raiz / "ciclos"

        ciclo = CicloLocalNivel10Nixal(
            diretorio_registros=registros
        )
        coordenador = CoordenadorFalso()

        executor = ExecutorCicloLocalNivel10Nixal(
            repositorio=raiz,
            branch="desenvolvimento",
            observador=ObservadorFalso(True),
            ciclo=ciclo,
            coordenador=coordenador,
        )

        resultado = executor.executar()

        assert resultado["estado"] == "aprovado"
        assert (
            resultado["commit_validado"]
            == "2" * 40
        )
        assert coordenador.validacoes == 1
        assert coordenador.testes == 1
        assert (
            resultado["ciclo"][
                "autorizacao_explicita"
            ]
            is False
        )

        historico = [
            item["para"]
            for item in resultado["ciclo"][
                "historico_estados"
            ]
        ]
        assert historico == [
            "alteracao_detectada",
            "sincronizacao_preparada",
            "validacao_em_execucao",
            "validacao_concluida",
            "aprovado",
        ]

        sem_alteracao = ExecutorCicloLocalNivel10Nixal(
            repositorio=raiz,
            branch="desenvolvimento",
            observador=ObservadorFalso(False),
            ciclo=ciclo,
            coordenador=coordenador,
        ).executar()

        assert sem_alteracao["estado"] == (
            "sem_alteracao"
        )
        assert (
            sem_alteracao["alteracao_detectada"]
            is False
        )

        # Falha de validação não chega a aprovado.
        coordenador_falha = CoordenadorFalso()
        coordenador_falha.validar_python_alterado = (
            lambda: {
                "sucesso": False,
                "erro": "falha_sintaxe",
            }
        )

        executor_falha = ExecutorCicloLocalNivel10Nixal(
            repositorio=raiz,
            branch="desenvolvimento",
            observador=ObservadorFalso(True),
            ciclo=CicloLocalNivel10Nixal(
                diretorio_registros=registros / "falha"
            ),
            coordenador=coordenador_falha,
        )

        resultado_falha = executor_falha.executar()
        assert resultado_falha["estado"] == (
            "rejeitado"
        )
        assert (
            resultado_falha["ciclo"][
                "resultado_validacao"
            ]["sucesso"]
            is False
        )

        # Exceção técnica durante validação também encerra o ciclo como
        # rejeitado, preservando o diagnóstico.
        coordenador_tecnico = CoordenadorFalhaTecnica()
        executor_tecnico = ExecutorCicloLocalNivel10Nixal(
            repositorio=raiz,
            branch="desenvolvimento",
            observador=ObservadorFalso(True),
            ciclo=CicloLocalNivel10Nixal(
                diretorio_registros=registros / "tecnico"
            ),
            coordenador=coordenador_tecnico,
        )
        resultado_tecnico = executor_tecnico.executar()
        assert resultado_tecnico["estado"] == "rejeitado"
        assert (
            "RuntimeError: falha_tecnica_teste"
            == resultado_tecnico["ciclo"][
                "resultado_validacao"
            ]["diagnostico"]
        )

    print("TESTE_NIVEL10_EXECUTOR_OK")
    print("OBSERVADOR_INTEGRADO=OK")
    print("COORDENADOR_INTEGRADO=OK")
    print("VALIDACAO_APROVADA=OK")
    print("VALIDACAO_REJEITADA=OK")
    print("SEM_AUTORIZACAO=OK")
    print("PASSOU: True")


if __name__ == "__main__":
    executar()
