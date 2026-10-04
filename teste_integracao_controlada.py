#!/usr/bin/env python3

"""Teste de regressão da integração controlada de desenvolvimento da Nyxal."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_integracao_controlada import (
    IntegracaoControladaDesenvolvimentoNixal,
)
from nixal_proposta_integracao import (
    PropostaIntegracaoDesenvolvimentoNixal,
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


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def preparar_repositorio(base_temporaria: Path) -> Path:
    raiz = base_temporaria / "repositorio"
    raiz.mkdir()

    git(raiz, "init", "-b", "main")
    git(raiz, "config", "user.name", "Nyxal Test")
    git(raiz, "config", "user.email", "nyxal-test@example.invalid")

    base = raiz / "base.txt"
    base.write_text("base\n", encoding="utf-8")
    git(raiz, "add", "base.txt")
    git(raiz, "commit", "-m", "base")
    return raiz


def preparar_fixture(base_temporaria: Path) -> tuple[Path, Path]:
    candidato = base_temporaria / "candidate"
    candidato.mkdir()

    codigo = candidato / "codigo.py"
    codigo.write_text(
        "def saudacao():\n    return 'NYXAL'\n",
        encoding="utf-8",
    )
    fingerprint = sha256(codigo)

    (candidato / "candidato.json").write_text(
        json.dumps(
            {
                "versao_registro": 1,
                "candidato_id": "candidato-001",
                "estado": "candidato",
                "arquivo": "codigo.py",
                "manifesto": "manifesto.json",
                "fingerprint": fingerprint,
                "avaliacao": {"aprovado": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    propostas_dir = base_temporaria / "propostas"
    propostas = PropostaIntegracaoDesenvolvimentoNixal(
        repositorio=base_temporaria / "repositorio",
        propostas=propostas_dir,
    )
    proposta = propostas.criar(
        candidato_dir=candidato,
        destino="main",
    )
    return candidato, Path(proposta["arquivo_proposta"])


def executar() -> None:
    with TemporaryDirectory() as temporario:
        base_temporaria = Path(temporario)
        raiz = preparar_repositorio(base_temporaria)
        _, proposta = preparar_fixture(base_temporaria)

        integrador = IntegracaoControladaDesenvolvimentoNixal(
            repositorio=raiz,
            propostas=base_temporaria / "propostas",
            autorizacoes=base_temporaria / "autorizacoes",
        )
        proposta_id = json.loads(
            proposta.read_text(encoding="utf-8")
        )["proposta_id"]

        # A barreira exige um registro externo de autorização.
        try:
            integrador.preparar(
                proposta_id=proposta_id,
                caminho_autorizacao=(
                    base_temporaria / "autorizacoes" / "inexistente.json"
                ),
            )
        except FileNotFoundError as erro:
            assert str(erro) == "arquivo_autorizacao_nao_encontrado"
        else:
            raise AssertionError(
                "integracao sem autorizacao externa foi permitida"
            )

        main_commit = git(raiz, "rev-parse", "main")
        assert git(raiz, "rev-parse", "main") == main_commit
        assert json.loads(
            proposta.read_text(encoding="utf-8")
        )["estado"] == "aguardando_autorizacao"

        # Fingerprint incorreto continua bloqueando antes da integração.
        dados = json.loads(proposta.read_text(encoding="utf-8"))
        autorizacoes = base_temporaria / "autorizacoes"
        autorizacoes.mkdir(parents=True, exist_ok=True)
        invalida = autorizacoes / "invalida.json"
        invalida.write_text(
            json.dumps(
                {
                    "autorizacao_id": "auth-invalida",
                    "proposta_id": proposta_id,
                    "autorizador": "humano-teste",
                    "motivo": "regressao",
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
                caminho_autorizacao=invalida,
            )
        except ValueError as erro:
            assert str(erro) == "fingerprint_autorizacao_inconsistente"
        else:
            raise AssertionError(
                "autorizacao com fingerprint incorreto foi aceita"
            )

        assert json.loads(
            proposta.read_text(encoding="utf-8")
        )["estado"] == "aguardando_autorizacao"
        assert git(raiz, "rev-parse", "main") == main_commit

        # Autorização válida prepara uma branch isolada sem alterar stable.
        fingerprint = dados["fingerprint"]
        valida = autorizacoes / "valida.json"
        valida.write_text(
            json.dumps(
                {
                    "autorizacao_id": "auth-valida",
                    "proposta_id": proposta_id,
                    "autorizador": "humano-teste",
                    "motivo": "regressao autorizada",
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
            caminho_autorizacao=valida,
            branch_integracao="integracao/integracao-candidato-001",
        )

        assert resultado["estado"] == "integracao_preparada"
        assert resultado["stable"] == "main"
        assert resultado["stable_modificada"] is False
        assert resultado["autorizacao_explicita"] is True
        assert resultado["commit_integracao"]

        assert git(raiz, "branch", "--show-current") == "main"
        assert not (raiz / "codigo.py").exists()

        integration_commit = git(
            raiz,
            "rev-parse",
            "refs/heads/integracao/integracao-candidato-001",
        )
        assert integration_commit == resultado["commit_integracao"]
        assert git(raiz, "rev-parse", "main") == main_commit
        assert git(
            raiz,
            "show",
            "main:base.txt",
        ) == "base"
        assert git(
            raiz,
            "show",
            "integracao/integracao-candidato-001:codigo.py",
        ) == "def saudacao():\n    return 'NYXAL'"

        # A árvore principal permanece intacta mesmo se houver sujeira local.
        (raiz / "alteracao.txt").write_text(
            "nao autorizada\n",
            encoding="utf-8",
        )
        assert git(raiz, "rev-parse", "main") == main_commit

        # Branch existente nunca é reutilizada.
        outro_candidato = base_temporaria / "candidate-2"
        outro_candidato.mkdir()
        outro_codigo = outro_candidato / "codigo.py"
        outro_codigo.write_text(
            "print('OUTRO')\n",
            encoding="utf-8",
        )
        outro_fp = sha256(outro_codigo)
        (outro_candidato / "candidato.json").write_text(
            json.dumps(
                {
                    "versao_registro": 1,
                    "candidato_id": "candidato-002",
                    "estado": "candidato",
                    "arquivo": "codigo.py",
                    "fingerprint": outro_fp,
                    "avaliacao": {"aprovado": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        propostas = PropostaIntegracaoDesenvolvimentoNixal(
            repositorio=raiz,
            propostas=base_temporaria / "propostas-2",
        )
        criado = propostas.criar(
            candidato_dir=outro_candidato,
            destino="main",
        )
        outro_id = criado["proposta_id"]
        outro_auth = autorizacoes / "outro.json"
        outro_auth.write_text(
            json.dumps(
                {
                    "autorizacao_id": "auth-outro",
                    "proposta_id": outro_id,
                    "autorizador": "humano-teste",
                    "motivo": "teste de branch existente",
                    "fingerprint": outro_fp,
                    "destino": "main",
                    "confirmacao_explicita": "AUTORIZAR_INTEGRACAO",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        integrador_outro = IntegracaoControladaDesenvolvimentoNixal(
            repositorio=raiz,
            propostas=base_temporaria / "propostas-2",
            autorizacoes=autorizacoes,
        )
        git(
            raiz,
            "branch",
            "integracao/integracao-candidato-002",
        )
        try:
            integrador_outro.preparar(
                proposta_id=outro_id,
                caminho_autorizacao=outro_auth,
                branch_integracao="integracao/integracao-candidato-002",
            )
        except FileExistsError as erro:
            assert str(erro) == "branch_de_integracao_ja_existente"
        else:
            raise AssertionError(
                "branch de integracao existente foi reutilizada"
            )

    print("TESTE_INTEGRACAO_CONTROLADA_OK")
    print("AUTORIZACAO_EXTERNA_OBRIGATORIA=OK")
    print("FINGERPRINT_VALIDADO=OK")
    print("STABLE_ISOLADA=OK")
    print("WORKTREE_ISOLADO=OK")
    print("REGRESSAO_BRANCH_EXISTENTE=OK")
    print("PASSOU: True")


if __name__ == "__main__":
    executar()
