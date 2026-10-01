#!/usr/bin/env python3

"""Teste do avaliador controlado de desenvolvimento da Nyxal."""

from nixal_avaliador_desenvolvimento import (
    AvaliacaoDesenvolvimentoNixal,
)


def executar() -> None:
    contrato = {
        "executar": False,
        "operacoes_permitidas": [
            "analise",
            "py_compile",
        ],
        "tipo": "python",
    }

    avaliacao = AvaliacaoDesenvolvimentoNixal.avaliar(
        contrato=contrato,
        validacao_python={
            "sucesso": True,
        },
    )

    assert avaliacao.aprovado is True
    assert all(
        avaliacao.criterios.values()
    )
    assert avaliacao.motivos == []

    rejeitada = AvaliacaoDesenvolvimentoNixal.avaliar(
        contrato={
            "executar": True,
            "operacoes_permitidas": [
                "analise",
            ],
            "tipo": "python",
        },
        validacao_python={
            "sucesso": False,
        },
    )

    assert rejeitada.aprovado is False
    assert (
        "execucao_desabilitada"
        in rejeitada.motivos
    )
    assert (
        "sintaxe_python_valida"
        in rejeitada.motivos
    )

    print(
        "TESTE_AVALIADOR_DESENVOLVIMENTO_OK"
    )


if __name__ == "__main__":
    executar()
