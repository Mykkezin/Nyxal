#!/usr/bin/env python3
"""Teste da barreira de autorização explícita antes da integração."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from nixal_integracao_controlada import (
    IntegracaoControladaDesenvolvimentoNixal,
)
from nixal_proposta_integracao import (
    PropostaIntegracaoDesenvolvimentoNixal,
)


def git(repo: Path, *args: str) -> str:
    resultado = subprocess.run(
        ["git", *args],
        cwd=repo,
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


def hash_arquivo(caminho: Path) -> str:
    return hashlib.sha256(
        caminho.read_bytes()
    ).hexdigest()


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
        base_sha = git(
            repo,
            "rev-parse",
            "refs/heads/main",
        )

        candidato_dir = (
            raiz
            / "Nyxal-candidates"
            / "candidato-test"
        )
        candidato_dir.mkdir(parents=True)

        candidato_arquivo = candidato_dir / "alvo.py"
        candidato_arquivo.write_text(
            "print('CANDIDATO')\n",
            encoding="utf-8",
        )
        fingerprint = hash_arquivo(
            candidato_arquivo
        )

        (candidato_dir / "candidato.json").write_text(
            json.dumps(
                {
                    "versao_registro": 1,
                    "candidato_id": "candidato-test",
                    "estado": "candidato",
                    "arquivo": "alvo.py",
                    "manifesto": "manifesto_evolucao.json",
                    "fingerprint": fingerprint,
                    "avaliacao": {
                        "aprovado": True
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        propostas_dir = (
            raiz / "Nyxal-integration-proposals"
        )
        propostas = PropostaIntegracaoDesenvolvimentoNixal(
            repositorio=repo,
            propostas=propostas_dir,
        )

        criado = propostas.criar(
            candidato_dir=candidato_dir,
            destino="main",
        )
        proposta_id = criado["proposta_id"]

        autorizacoes_dir = (
            raiz
            / "Nyxal-integration-authorizations"
        )
        integrador = IntegracaoControladaDesenvolvimentoNixal(
            repositorio=repo,
            propostas=propostas_dir,
            autorizacoes=autorizacoes_dir,
        )

        # Sem arquivo externo de autorização: bloqueio antes de qualquer
        # mudança no Git ou na proposta.
        try:
            integrador.preparar(
                proposta_id=proposta_id,
                caminho_autorizacao=(
                    autorizacoes_dir / "inexistente.json"
                ),
            )
            raise AssertionError(
                "autorizacao ausente deveria bloquear"
            )
        except FileNotFoundError as erro:
            assert str(erro) == (
                "arquivo_autorizacao_nao_encontrado"
            )

        assert git(
            repo,
            "rev-parse",
            "refs/heads/main",
        ) == base_sha
        assert propostas.consultar(
            proposta_id
        )["estado"] == "aguardando_autorizacao"

        # Autorização com fingerprint divergente também não pode liberar.
        autorizacao_invalida = (
            autorizacoes_dir / "invalida.json"
        )
        autorizacao_invalida.write_text(
            json.dumps(
                {
                    "autorizacao_id": "auth-invalida",
                    "proposta_id": proposta_id,
                    "autorizador": "humano-teste",
                    "motivo": "teste de bloqueio",
                    "fingerprint": "0" * 64,
                    "destino": "main",
                    "confirmacao_explicita": (
                        "AUTORIZAR_INTEGRACAO"
                    ),
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
        assert git(
            repo,
            "rev-parse",
            "refs/heads/main",
        ) == base_sha

        # Autorização válida: cria somente uma branch de integração.
        autorizacao_valida = (
            autorizacoes_dir / "valida.json"
        )
        autorizacao_valida.write_text(
            json.dumps(
                {
                    "autorizacao_id": "auth-valida",
                    "proposta_id": proposta_id,
                    "autorizador": "humano-teste",
                    "motivo": (
                        "melhoria aprovada para revisão"
                    ),
                    "fingerprint": fingerprint,
                    "destino": "main",
                    "confirmacao_explicita": (
                        "AUTORIZAR_INTEGRACAO"
                    ),
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

        assert resultado["estado"] == (
            "integracao_preparada"
        )
        assert resultado["autorizacao_explicita"] is True
        assert resultado["stable_modificada"] is False

        estado = propostas.consultar(
            proposta_id
        )
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

        assert branch_sha == resultado[
            "commit_integracao"
        ]
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

        # git() usa stdout.strip(); aqui a comparação deve refletir o conteúdo
        # textual sem o terminador de linha final.
        assert stable_arquivo == "print('STABLE')"
        assert integrado_arquivo == "print('CANDIDATO')"

        parentes = git(
            repo,
            "rev-list",
            "--parents",
            "-n",
            "1",
            branch_sha,
        ).split()
        assert parentes[1] == base_sha

        historico = estado["historico_estados"]
        assert [
            item["para"]
            for item in historico
        ] == [
            "aguardando_autorizacao",
            "autorizada_para_integracao",
            "integracao_preparada",
        ]

    print("=" * 64)
    print("TESTE — AUTORIZAÇÃO EXPLÍCITA → INTEGRAÇÃO CONTROLADA")
    print("=" * 64)
    print("BLOQUEIO_SEM_AUTORIZACAO=OK")
    print("BLOQUEIO_FINGERPRINT_INCORRETO=OK")
    print("AUTORIZACAO_EXPLICITA_VALIDADA=OK")
    print("BRANCH_INTEGRACAO_CRIADA=OK")
    print("STABLE_NAO_MODIFICADA=OK")
    print("CANDIDATO_ISOLADO_NA_BRANCH=OK")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
