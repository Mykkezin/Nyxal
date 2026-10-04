#!/usr/bin/env python3
"""Teste determinístico do observador do Nível 10."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_observador_desenvolvimento import (
    ObservadorDesenvolvimentoNixal,
)


def git(repositorio: Path, *args: str) -> str:
    processo = subprocess.run(
        ["git", *args],
        cwd=repositorio,
        text=True,
        capture_output=True,
        check=False,
    )
    assert processo.returncode == 0, (
        f"git_falhou:{args}:{processo.stderr}"
    )
    return processo.stdout.strip()


def executar() -> None:
    with TemporaryDirectory() as temporario:
        raiz = Path(temporario)

        git(raiz, "init", "-b", "desenvolvimento")
        git(
            raiz,
            "config",
            "user.name",
            "Nyxal Test",
        )
        git(
            raiz,
            "config",
            "user.email",
            "nyxal-test@example.invalid",
        )

        arquivo = raiz / "estado.txt"
        arquivo.write_text(
            "primeiro\n",
            encoding="utf-8",
        )
        git(raiz, "add", "estado.txt")
        git(raiz, "commit", "-m", "estado inicial")

        estado_path = raiz / "reports" / "nivel10.json"

        observador = (
            ObservadorDesenvolvimentoNixal(
                repositorio=raiz,
                branch="desenvolvimento",
                estado_path=estado_path,
            )
        )

        primeiro = observador.observar()

        assert primeiro["estado"] == "observado"
        assert primeiro["alteracao_detectada"] is False
        assert primeiro["ciclo"] is None

        commit_inicial = primeiro["commit_observado"]
        assert len(commit_inicial) == 40

        segundo = observador.observar()
        assert segundo["alteracao_detectada"] is False
        assert segundo["commit_observado"] == commit_inicial

        arquivo.write_text(
            "segundo\n",
            encoding="utf-8",
        )
        git(raiz, "add", "estado.txt")
        git(raiz, "commit", "-m", "segunda alteração")

        commit_novo = git(
            raiz,
            "rev-parse",
            "refs/heads/desenvolvimento",
        )

        terceiro = observador.observar()

        assert terceiro["alteracao_detectada"] is True
        assert terceiro["estado"] == "alteracao_detectada"
        assert terceiro["commit_anterior"] == commit_inicial
        assert terceiro["commit_novo"] == commit_novo

        ciclo = terceiro["ciclo"]
        assert ciclo["estado"] == "alteracao_detectada"
        assert ciclo["ciclo_id"].startswith("n10-")

        quarto = observador.observar()
        assert quarto["alteracao_detectada"] is False

        registro = json.loads(
            estado_path.read_text(encoding="utf-8")
        )
        assert registro["ultimo_commit_observado"] == commit_novo
        assert len(registro["historico_ciclos"]) == 1

        ciclo_registrado = registro["historico_ciclos"][0]
        assert ciclo_registrado["ciclo_id"] == ciclo["ciclo_id"]

        git_before = git(
            raiz,
            "rev-parse",
            "refs/heads/desenvolvimento",
        )

        reloaded = ObservadorDesenvolvimentoNixal(
            repositorio=raiz,
            branch="desenvolvimento",
            estado_path=estado_path,
        )
        quinto = reloaded.observar()

        git_after = git(
            raiz,
            "rev-parse",
            "refs/heads/desenvolvimento",
        )

        assert quinto["alteracao_detectada"] is False
        assert git_before == git_after

        # A API formal Nível 10 não substitui o observador legado.
        assert hasattr(observador, "ciclo")
        assert hasattr(observador, "iniciar")
        assert hasattr(observador, "parar")

        # Estado persistente adulterado deve ser rejeitado.
        adulterado = json.loads(
            estado_path.read_text(encoding="utf-8")
        )
        adulterado["ultimo_commit_observado"] = "0" * 40
        estado_path.write_text(
            json.dumps(adulterado, ensure_ascii=False),
            encoding="utf-8",
        )

        try:
            reloaded.observar()
        except ValueError as erro:
            assert str(erro) == "ultimo_commit_inconsistente"
        else:
            raise AssertionError(
                "estado_adulterado_aceito"
            )

    print("TESTE_NIVEL10_OBSERVADOR_OK")
    print("DETECCAO_COMMIT_NOVO=OK")
    print("SEM_FALSO_POSITIVO=OK")
    print("CICLO_ID_DETERMINISTICO=OK")
    print("ESTADO_PERSISTENTE=OK")
    print("SEM_ALTERACAO_GIT=OK")
    print("LEGADO_PRESERVADO=OK")
    print("ESTADO_ADULTERADO_BLOQUEADO=OK")
    print("PASSOU: True")


if __name__ == "__main__":
    executar()
