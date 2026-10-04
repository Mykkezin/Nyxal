#!/usr/bin/env python3
"""Teste determinístico da máquina de estados do Nível 10."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_ciclo_local_nivel10 import (
    CicloLocalNivel10Nixal,
)


def executar() -> None:
    anterior = "1" * 40
    novo = "2" * 40

    with TemporaryDirectory() as temporario:
        registros = Path(temporario) / "ciclos"
        ciclo = CicloLocalNivel10Nixal(
            diretorio_registros=registros
        )

        observacao = {
            "alteracao_detectada": True,
            "ciclo": {
                "ciclo_id": ciclo._ciclo_id(
                    branch="desenvolvimento",
                    commit_anterior=anterior,
                    commit_novo=novo,
                ),
                "branch": "desenvolvimento",
                "commit_anterior": anterior,
                "commit_novo": novo,
            },
        }

        aberto = ciclo.abrir_ciclo(
            observacao
        )
        assert aberto["estado"] == (
            "alteracao_detectada"
        )
        ciclo_id = aberto["ciclo_id"]

        preparado = ciclo.registrar_sincronizacao_preparada(
            ciclo_id,
            commit_validado=novo,
            evidencias=["estado_git_limpo"],
        )
        assert preparado["estado"] == (
            "sincronizacao_preparada"
        )

        executando = ciclo.iniciar_validacao(
            ciclo_id
        )
        assert executando["estado"] == (
            "validacao_em_execucao"
        )

        concluido = ciclo.concluir_validacao(
            ciclo_id,
            sucesso=True,
            validacoes=[
                {
                    "nome": "py_compile",
                    "sucesso": True,
                }
            ],
        )
        assert concluido["estado"] == (
            "validacao_concluida"
        )

        aprovado = ciclo.classificar_resultado(
            ciclo_id
        )
        assert aprovado["estado"] == "aprovado"
        assert aprovado[
            "autorizacao_explicita"
        ] is False

        esperado = [
            "alteracao_detectada",
            "sincronizacao_preparada",
            "validacao_em_execucao",
            "validacao_concluida",
            "aprovado",
        ]
        assert [
            item["para"]
            for item in aprovado[
                "historico_estados"
            ]
        ] == esperado

        assert ciclo.consultar(
            ciclo_id
        )["ciclo_id"] == ciclo_id

        # Um ciclo idêntico é idempotente na abertura.
        repetido = ciclo.abrir_ciclo(
            observacao
        )
        assert repetido["ciclo_id"] == ciclo_id
        assert len(
            repetido["historico_estados"]
        ) == len(esperado)

        # Commit diferente não pode ser apresentado como o mesmo ciclo.
        try:
            ciclo.registrar_sincronizacao_preparada(
                ciclo_id,
                commit_validado="3" * 40,
            )
        except ValueError as erro:
            assert str(erro) == (
                "estado_invalido_para_sincronizacao"
            )
        else:
            raise AssertionError(
                "transicao_terminal_aceita"
            )

        # Fluxo de rejeição.
        rejeicao_observacao = {
            "alteracao_detectada": True,
            "ciclo": {
                "ciclo_id": ciclo._ciclo_id(
                    branch="desenvolvimento",
                    commit_anterior=novo,
                    commit_novo="3" * 40,
                ),
                "branch": "desenvolvimento",
                "commit_anterior": novo,
                "commit_novo": "3" * 40,
            },
        }

        rejeicao = ciclo.abrir_ciclo(
            rejeicao_observacao
        )
        ciclo_id_rejeicao = rejeicao["ciclo_id"]

        ciclo.registrar_sincronizacao_preparada(
            ciclo_id_rejeicao,
            commit_validado="3" * 40,
        )
        ciclo.iniciar_validacao(
            ciclo_id_rejeicao
        )
        ciclo.concluir_validacao(
            ciclo_id_rejeicao,
            sucesso=False,
            diagnostico="teste_falhou",
        )
        final_rejeicao = ciclo.classificar_resultado(
            ciclo_id_rejeicao
        )

        assert final_rejeicao["estado"] == "rejeitado"
        assert (
            final_rejeicao["resultado_validacao"][
                "diagnostico"
            ]
            == "teste_falhou"
        )

        # Transição ilegal a partir de estado inicial deve bloquear.
        novo_ciclo = ciclo.abrir_ciclo(
            {
                "alteracao_detectada": True,
                "ciclo": {
                    "ciclo_id": ciclo._ciclo_id(
                        branch="desenvolvimento",
                        commit_anterior="4" * 40,
                        commit_novo="5" * 40,
                    ),
                    "branch": "desenvolvimento",
                    "commit_anterior": "4" * 40,
                    "commit_novo": "5" * 40,
                },
            }
        )

        try:
            ciclo.classificar_resultado(
                novo_ciclo["ciclo_id"]
            )
        except ValueError as erro:
            assert str(erro) == (
                "estado_invalido_para_classificacao"
            )
        else:
            raise AssertionError(
                "transicao_ilegal_aceita"
            )

        # Persistência realmente legível.
        caminho = registros / (
            f"{ciclo_id}.json"
        )
        assert caminho.is_file()
        json.loads(
            caminho.read_text(
                encoding="utf-8"
            )
        )

    print("TESTE_NIVEL10_CICLO_LOCAL_OK")
    print("TRANSICOES_VALIDAS=OK")
    print("APROVACAO_SEM_AUTORIZACAO=OK")
    print("REJEICAO_VALIDADA=OK")
    print("IDEMPOTENCIA_DE_ABERTURA=OK")
    print("PERSISTENCIA=OK")
    print("PASSOU: True")


if __name__ == "__main__":
    executar()
