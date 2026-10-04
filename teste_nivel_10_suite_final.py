#!/usr/bin/env python3
"""Suíte consolidada determinística do Nível 10."""

from __future__ import annotations

import subprocess
import sys


TESTES = [
    "teste_nivel_10_contrato.py",
    "teste_nivel_10_observador_desenvolvimento.py",
    "teste_nivel_10_ciclo_local.py",
    "teste_nivel_10_executor.py",
]


def executar() -> None:
    resultados = []

    for teste in TESTES:
        processo = subprocess.run(
            [sys.executable, teste],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )

        resultados.append(
            {
                "teste": teste,
                "codigo_saida": processo.returncode,
                "sucesso": processo.returncode == 0,
                "saida": processo.stdout.strip(),
                "erro": processo.stderr.strip(),
            }
        )

    falhas = [
        item
        for item in resultados
        if not item["sucesso"]
    ]

    for item in resultados:
        print(
            f"{item['teste']}: "
            f"{'OK' if item['sucesso'] else 'FALHOU'}"
        )
        if item["saida"]:
            print(item["saida"])
        if item["erro"]:
            print(item["erro"])

    assert not falhas, (
        "falha_suite_nivel10:"
        + ",".join(
            item["teste"]
            for item in falhas
        )
    )

    print("SUITE_NIVEL10_OK")
    print("CONTRATO=OK")
    print("OBSERVADOR=OK")
    print("CICLO_LOCAL=OK")
    print("EXECUTOR=OK")
    print("PASSOU: True")


if __name__ == "__main__":
    executar()
