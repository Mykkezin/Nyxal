#!/usr/bin/env python3

"""
TESTE DO COORDENADOR DE DESENVOLVIMENTO DA NYXAL

Valida os contratos básicos do coordenador sem modificar o repositório.

O coordenador lê o Git real do diretório que recebe (`branch_atual` vem de
`git branch --show-current`, `arvore_limpa` de `git status --porcelain`).
Apontá-lo para o checkout onde o teste roda amarra o resultado ao ambiente:
na branch, no commit e na sujeira de quem executa. Aqui o repositório é um
depósito descartável criado em um estado Git conhecido, o que preserva todas
as asserções originais e as torna determinísticas.
"""

import subprocess
import tempfile
from pathlib import Path

from nixal_coordenador_desenvolvimento import (
    CoordenadorDesenvolvimentoNixal,
)

BRANCH = "desenvolvimento/mcp-bridge"


def criar_repositorio(repositorio: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=Nyxal Test",
             "-c", "user.email=teste@nyxal.local", *args],
            cwd=repositorio,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "--quiet")
    git("checkout", "-q", "-b", BRANCH)
    (repositorio / "README.md").write_text("depósito do teste\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "estado inicial do depósito de teste")
    # `arquivos_ultimo_commit` compara HEAD com HEAD^: com um único commit o
    # próprio Git falha e o coordenador devolve []. São precisos dois commits
    # para que a descoberta de arquivos seja observável de verdade.
    (repositorio / "modulo.py").write_text("VALOR = 1\n", encoding="utf-8")
    (repositorio / "teste_modulo.py").write_text(
        "def testar():\n    assert True\n", encoding="utf-8"
    )
    git("add", "-A")
    git("commit", "-q", "-m", "adiciona módulo e teste ao depósito")


def executar() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        repositorio = Path(temporario) / "deposito"
        repositorio.mkdir()
        criar_repositorio(repositorio)

        coordenador = CoordenadorDesenvolvimentoNixal(
            repositorio=repositorio,
            branch=BRANCH,
        )

        estado = coordenador.estado()

        assert isinstance(estado, dict)

        assert estado["repositorio"] == str(repositorio)

        assert estado["branch_atual"] == (
            BRANCH
        )

        assert estado["branch_alvo"] == (
            BRANCH
        )

        assert isinstance(
            estado["arvore_limpa"],
            bool,
        )

        assert isinstance(
            estado["status"],
            list,
        )

        # O depósito foi criado commitsado e limpo: a asserção deixa de
        # depender de "pode ser bool" para verificar o estado real.
        assert estado["arvore_limpa"] is True

        assert estado["status"] == []

        esperado_arvore_limpa = (
            len(estado["status"]) == 0
        )

        assert estado["arvore_limpa"] == (
            esperado_arvore_limpa
        )

        arquivos = coordenador.arquivos_ultimo_commit()

        assert isinstance(arquivos, list)

        assert arquivos == [
            "modulo.py",
            "teste_modulo.py",
        ]

        arquivos_python = (
            coordenador.arquivos_python_ultimo_commit()
        )

        assert isinstance(
            arquivos_python,
            list,
        )

        assert arquivos_python == ["modulo.py", "teste_modulo.py"]

        for arquivo in arquivos_python:
            assert arquivo.endswith(".py")

        testes = (
            coordenador.testes_python_ultimo_commit()
        )

        assert isinstance(testes, list)

        assert testes == ["teste_modulo.py"]

        for teste in testes:
            assert Path(teste).name.startswith(
                "teste_"
            )

        # Um depósito sujo precisa ser reportado como sujo: sem isso o teste
        # não distingue "árvore limpa" de "git status falhou silenciosamente".
        (repositorio / "modulo.py").write_text("VALOR = 2\n", encoding="utf-8")
        estado_sujo = coordenador.estado()
        assert estado_sujo["arvore_limpa"] is False
        assert estado_sujo["status"] == ["M modulo.py"]

    print(
        "TESTE_COORDENADOR_DESENVOLVIMENTO_OK"
    )


if __name__ == "__main__":
    executar()
