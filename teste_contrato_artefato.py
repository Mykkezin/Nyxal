#!/usr/bin/env python3

"""Teste do contrato declarativo de artefatos da Nyxal."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_contrato_artefato import (
    ContratoArtefatoNixal,
)


def executar() -> None:
    with TemporaryDirectory() as temporario:
        raiz = Path(temporario)

        manifesto = raiz / "artefato.nyxal.json"
        manifesto.write_text(
            json.dumps(
                {
                    "versao_contrato": 1,
                    "nome": "teste",
                    "objetivo": "validar contrato",
                    "tipo": "python",
                    "arquivo": "teste.py",
                    "operacoes_permitidas": [
                        "analise",
                        "py_compile",
                    ],
                    "executar": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        contrato = ContratoArtefatoNixal.carregar(
            manifesto
        )

        assert contrato.nome == "teste"
        assert contrato.tipo == "python"
        assert contrato.arquivo == "teste.py"
        assert contrato.executar is False

        manifesto.write_text(
            json.dumps(
                {
                    "versao_contrato": 1,
                    "nome": "inseguro",
                    "objetivo": "teste",
                    "tipo": "python",
                    "arquivo": "teste.py",
                    "operacoes_permitidas": [
                        "comando_arbitrario"
                    ],
                    "executar": False,
                }
            ),
            encoding="utf-8",
        )

        try:
            ContratoArtefatoNixal.carregar(
                manifesto
            )
        except ValueError as erro:
            assert str(erro) == (
                "operacao_nao_permitida"
            )
        else:
            raise AssertionError(
                "contrato inseguro foi aceito"
            )

        manifesto.write_text(
            json.dumps(
                {
                    "versao_contrato": 1,
                    "nome": "execucao",
                    "objetivo": "teste",
                    "tipo": "python",
                    "arquivo": "teste.py",
                    "operacoes_permitidas": [
                        "analise",
                        "py_compile",
                    ],
                    "executar": True,
                }
            ),
            encoding="utf-8",
        )

        try:
            ContratoArtefatoNixal.carregar(
                manifesto
            )
        except ValueError as erro:
            assert str(erro) == (
                "execucao_de_codigo_nao_permitida"
            )
        else:
            raise AssertionError(
                "contrato executavel foi aceito"
            )

    print(
        "TESTE_CONTRATO_ARTEFATO_OK"
    )


if __name__ == "__main__":
    executar()
