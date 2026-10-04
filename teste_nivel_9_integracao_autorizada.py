#!/usr/bin/env python3
"""Teste da barreira de autorização explícita para integração."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from nixal_integracao_controlada import (
    IntegracaoControladaDesenvolvimentoNixal,
)
from nixal_proposta_integracao import (
    PropostaIntegracaoDesenvolvimentoNixal,
)


def git(repo: Path, *args: str, cwd: Path | None = None) -> str:
    resultado = subprocess.run(
        ["git", *args],
        cwd=cwd or repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} falhou: "
            f"{resultado.stderr.strip()}"
        )
    return resultado.stdout.strip()


def sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    digest.update(caminho.read_bytes())
    return digest.hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="nyxal-integracao-autorizada-"
    ) as diretorio:
        raiz = Path(diretorio)
        repo = raiz / "repo"
        repo.mkdir()

        git(repo, "init", "-b", "main")
        git(repo, "config", "user.name", "Nyxal Test")
        git(repo, "config", "user.email", "nyxal@test.local")

        alvo = repo / "alvo.py"
        alvo.write_text(
            "print('STABLE')\n",
            encoding="utf-8",
        )
        git(repo, "add", "alvo.py")
        git(repo, "commit", "-m", "base")
        base_sha = git(repo, "rev-parse", "refs/heads/main")

        git(repo, "switch", "-c", "workspace")

        candidato_dir = raiz / "Nyxal-candidates" / "candidato-test"
        candidato_dir.mkdir(parents=True)

        candidato_arquivo = candidato_dir / "alvo.py"
        candidato_arquivo.write_text(
            "print('CANDIDATO')\n",
            encoding="utf-8",
        )
        fingerprint = sha256(candidato_arquivo)

        candidato = {
            "versao_registro": 1,
            "candidato_id": "candidato-test",
            "estado": "candidato",
            "arquivo": "alvo.py",
            "manifesto": "manifesto_evolucao.json",
            "fingerprint": fingerprint,
            "avaliacao": {
                "aprovado": True,
            },
        }
        (candidato_dir / "candidato.json").write_text(
            json.dumps(
                candidato,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        propostas_dir = raiz / "Nyxal-integration-proposals"
        propostas = PropostaIntegracaoDesenvolvimentoNixal(
            repositorio=repo,
            propostas=propostas_dir,
        )
        criado = propostas.criar(
            candidato_dir=candidato_dir,
            destino="main",
        )
        proposta_id = criado["proposta_id"]

        autorizacoes_dir = raiz / "Nyxal-integration-authorizations"
        integrador = IntegracaoControladaDesenvolvimentoNixal(
            repositorio=repo,
            propostas=propostas_dir,
            autorizacoes=autorizacoes_dir,
        )

        try:
            integrador.preparar(
                proposta_id=proposta_id,
                caminho_autorizacao=autorizacoes_dir / "nao-existe.json",
            )
            raise AssertionError(
                "autorizacao ausente deveria bloquear"
            )
        except FileNotFoundError as erro:
            assert str(erro) == (
                "arquivo_autorizacao_nao_encontrado"
            )

        depois_sem_auth = git(
            repo,
            "rev-parse",
            "refs/heads/main",
        )
        assert depois_sem_auth == base_sha
        assert propostas.consultar(
            proposta_id
        )["estado"] == "aguardando_autorizacao"

        autorizacao_invalida = autorizacoes_dir / "invalida.json"
        autorizacao_invalida.write_text(
            json.dumps(
                {
                    "autorizacao_id": "auth-invalida",
                    "proposta_id": proposta_id,
                    "autorizador": "humano-teste",
                    "motivo": "teste de bloqueio",
                    "fingerprint": "0" * 64,
                    "destino": "main",
                    "confirmacao_explicita": "AUTORIZAR_INTEGRACAO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        try:
            integrador.preparar(
                proposta_id=proposta_id,
                caminho_autorizacao=autorizacao_invalida,
            )
            raise AssertionError(
                "fingerprint invalido deveria bloquear"
            )
        except ValueError as erro:
            assert str(erro) == (
                "fingerprint_autorizacao_inconsistente"
            )

        assert propostas.consultar(
            proposta_id
        )["estado"] == "aguardando_autorizacao"

        autorizacao_valida = autorizacoes_dir / "valida.json"
        autorizacao_valida.write_text(
            json.dumps(
                {
                    "autorizacao_id": "auth-valida",
                    "proposta_id": proposta_id,
                    "autorizador": "humano-teste",
                    "motivo": "melhoria aprovada para revisão",
                    "fingerprint": fingerprint,
                    "destino": "main",
                    "confirmacao_explicita": "AUTORIZAR_INTEGRACAO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        resultado = integrador.preparar(
            proposta_id=proposta_id,
            caminho_autorizacao=autorizacao_valida,
        )

        assert resultado["sucesso"] if "sucesso" in resultado else True
        assert resultado["estado"] == "integracao_preparada"
        assert resultado["autorizacao_explicita"] is True
        assert resultado["stable_modificada"] is False

        estado = propostas.consultar(proposta_id)
        assert estado["estado"] == "integracao_preparada"
        assert estado["autorizacao_explicita"] is True
        assert estado["integracao_executada"] is False
        assert estado["stable_modificada"] is False

        branch = resultado["branch_integracao"]
        branch_sha = git(
            repo,
            "rev-parse",
            f"refs/heads/{branch}",
        )
        assert branch_sha == resultado["commit_integracao"]
        assert git(
            repo,
            "rev-parse",
            "refs/heads/main",
        ) == base_sha

        stable_arquivo = git(
            repo,
            "show",
            "refs/heads/main:alvo.py",
        )
        integrado_arquivo = git(
            repo,
            "show",
            f"refs/heads/{branch}:alvo.py",
        )

        assert stable_arquivo == "print('STABLE')\n"
        assert integrado_arquivo == "print('CANDIDATO')\n"

        parentes = git(
            repo,
            "rev-list",
            "--parents",
            "-n",
            "1",
            branch_sha,
        ).split()
        assert parentes[1] == base_sha

    print("=" * 64)
    print("TESTE — INTEGRAÇÃO POR AUTORIZAÇÃO EXPLÍCITA")
    print("=" * 64)
    print("BLOQUEIO_SEM_AUTORIZACAO=OK")
    print("BLOQUEIO_FINGERPRINT_INCORRETO=OK")
    print("AUTORIZACAO_EXPLICITA_VALIDADA=OK")
    print("BRANCH_INTEGRACAO_CRIADA=OK")
    print("STABLE_NAO_MODIFICADA=OK")
    print("CANDIDATO_NA_BRANCH_AUTORIZADA=OK")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
