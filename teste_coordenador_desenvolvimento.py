#!/usr/bin/env python3

"""
TESTE DO COORDENADOR DE DESENVOLVIMENTO DA NYXAL

Valida os contratos básicos do coordenador sem modificar o repositório.
"""

from pathlib import Path

from nixal_coordenador_desenvolvimento import (
    CoordenadorDesenvolvimentoNixal,
)


def executar() -> None:
    repositorio = Path(__file__).resolve().parent

    coordenador = CoordenadorDesenvolvimentoNixal(
        repositorio=repositorio,
        branch="desenvolvimento/mcp-bridge",
    )

    estado = coordenador.estado()

    assert isinstance(estado, dict)

    assert estado["repositorio"] == str(repositorio)

    assert estado["branch_atual"] == (
        "desenvolvimento/mcp-bridge"
    )

    assert estado["branch_alvo"] == (
        "desenvolvimento/mcp-bridge"
    )

    assert isinstance(
        estado["arvore_limpa"],
        bool,
    )

    assert isinstance(
        estado["status"],
        list,
    )

    esperado_arvore_limpa = (
        len(estado["status"]) == 0
    )

    assert estado["arvore_limpa"] == (
        esperado_arvore_limpa
    )

    arquivos = coordenador.arquivos_ultimo_commit()

    assert isinstance(arquivos, list)

    arquivos_python = (
        coordenador.arquivos_python_ultimo_commit()
    )

    assert isinstance(
        arquivos_python,
        list,
    )

    for arquivo in arquivos_python:
        assert arquivo.endswith(".py")

    testes = (
        coordenador.testes_python_ultimo_commit()
    )

    assert isinstance(testes, list)

    for teste in testes:
        assert Path(teste).name.startswith(
            "teste_"
        )

    print(
        "TESTE_COORDENADOR_DESENVOLVIMENTO_OK"
    )


if __name__ == "__main__":
    executar()
