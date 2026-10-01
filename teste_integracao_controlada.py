#!/usr/bin/env python3

"""Teste da integração controlada de desenvolvimento da Nyxal."""

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_integracao_controlada import (
    IntegracaoControladaDesenvolvimentoNixal,
)


def git(raiz: Path, *args: str) -> str:
    resultado = subprocess.run(
        ["git", *args],
        cwd=raiz,
        text=True,
        capture_output=True,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
    return resultado.stdout.strip()


def executar() -> None:
    with TemporaryDirectory() as temporario:
        base_temporaria = Path(temporario)
        raiz = base_temporaria / "repositorio"
        raiz.mkdir()

        git(raiz, "init", "-b", "main")
        git(raiz, "config", "user.name", "Nyxal Test")
        git(raiz, "config", "user.email", "nyxal-test@example.invalid")

        base = raiz / "base.txt"
        base.write_text("base\n", encoding="utf-8")
        git(raiz, "add", "base.txt")
        git(raiz, "commit", "-m", "base")

        candidato = base_temporaria / "candidate"
        candidato.mkdir()
        (candidato / "candidato.json").write_text(
            json.dumps(
                {
                    "candidato_id": "candidato-001",
                    "estado": "candidato",
                    "arquivo": "codigo.py",
                    "avaliacao": {"aprovado": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (candidato / "codigo.py").write_text(
            "def saudacao():\n    return 'NYXAL'\n",
            encoding="utf-8",
        )

        proposta = base_temporaria / "proposta.json"
        proposta.write_text(
            json.dumps(
                {
                    "proposta_id": "integracao-candidato-001",
                    "estado": "aguardando_autorizacao",
                    "candidato_dir": str(candidato),
                    "autorizacao_explicita": False,
                    "integracao_executada": False,
                    "stable_modificada": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        integrador = (
            IntegracaoControladaDesenvolvimentoNixal(
                repositorio=raiz
            )
        )

        try:
            integrador.preparar(
                proposta_path=proposta
            )
        except PermissionError as erro:
            assert str(erro) == (
                "autorizacao_explicita_obrigatoria"
            )
        else:
            raise AssertionError(
                "integracao sem autorizacao foi permitida"
            )

        resultado = integrador.preparar(
            proposta_path=proposta,
            autorizacao_explicita=True,
        )

        assert resultado["estado"] == (
            "integracao_preparada"
        )
        assert resultado["stable"] == "main"
        assert resultado["branch_integracao"] == (
            "integracao/integracao-candidato-001"
        )
        assert resultado["stable_modificada"] is False
        assert resultado["push_executado"] is False
        assert resultado["pr_criada"] is False
        assert resultado["merge_executado"] is False
        assert resultado["commit_integracao"]

        assert git(raiz, "branch", "--show-current") == (
            "integracao/integracao-candidato-001"
        )
        assert (raiz / "codigo.py").exists()

        main_commit = git(
            raiz,
            "rev-parse",
            "main",
        )
        integration_commit = git(
            raiz,
            "rev-parse",
            "HEAD",
        )

        assert main_commit != integration_commit
        assert git(
            raiz,
            "show",
            "main:base.txt",
        ) == "base"

        assert git(
            raiz,
            "status",
            "--porcelain",
        ) == ""

    print(
        "TESTE_INTEGRACAO_CONTROLADA_OK"
    )


if __name__ == "__main__":
    executar()
