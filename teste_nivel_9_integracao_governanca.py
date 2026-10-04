#!/usr/bin/env python3
"""Teste da governança final do Nível 9."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_governanca_evolucao import GovernancaEvolucaoNixal
from nixal_proposta_integracao import PropostaIntegracaoDesenvolvimentoNixal


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


def preparar_repositorio(raiz: Path) -> Path:
    raiz.mkdir()
    git(raiz, "init", "-b", "main")
    git(raiz, "config", "user.name", "Nyxal Test")
    git(raiz, "config", "user.email", "nyxal-test@example.invalid")

    base = raiz / "base.txt"
    base.write_text("base\n", encoding="utf-8")
    git(raiz, "add", "base.txt")
    git(raiz, "commit", "-m", "base")
    return raiz


def preparar_candidato(raiz: Path) -> tuple[Path, Path]:
    candidato = raiz.parent / "candidate"
    candidato.mkdir()

    codigo = candidato / "codigo.py"
    codigo.write_text(
        "def saudacao():\\n    return 'NYXAL'\\n",
        encoding="utf-8",
    )
    import hashlib
    fingerprint = hashlib.sha256(codigo.read_bytes()).hexdigest()

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
        ),
        encoding="utf-8",
    )

    propostas = PropostaIntegracaoDesenvolvimentoNixal(
        repositorio=raiz,
        propostas=raiz.parent / "propostas",
    )
    proposta = propostas.criar(
        candidato_dir=candidato,
        destino="main",
    )
    return candidato, Path(proposta["arquivo_proposta"])


def executar() -> None:
    with TemporaryDirectory() as temporario:
        raiz = preparar_repositorio(Path(temporario) / "repo")
        _, proposta = preparar_candidato(raiz)

        governanca = GovernancaEvolucaoNixal(
            repositorio=raiz,
            governanca=raiz.parent / "governanca",
        )

        try:
            governanca.preparar_integracao(
                proposta_path=proposta
            )
        except ValueError as erro:
            assert str(erro) == "autorizacao_nao_registrada"
        else:
            raise AssertionError(
                "preparacao sem autorizacao foi permitida"
            )

        proposta_original = proposta.read_bytes()

        autorizada = governanca.autorizar_proposta(
            proposta_path=proposta,
            autorizador="operador_humano",
            motivo="Aprovacao explicita para integrar o candidato.",
        )
        assert autorizada["estado"] == "autorizada"
        assert autorizada["autorizacao"]["autorizacao_explicita"] is True
        assert autorizada["integracao_executada"] is False
        assert autorizada["stable_modificada"] is False

        # Qualquer alteração na proposta depois da autorização invalida a preparação.
        dados = json.loads(proposta.read_text(encoding="utf-8"))
        dados["destino_sugerido"] = "main-alterada"
        proposta.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        try:
            governanca.preparar_integracao(proposta_path=proposta)
        except ValueError as erro:
            assert str(erro) == "proposta_alterada_apos_autorizacao"
        else:
            raise AssertionError("proposta alterada foi aceita após autorização")

        dados["destino_sugerido"] = "main"
        proposta.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")

        # Restaurar exatamente o conteúdo autorizado não é suficiente: o hash
        # precisa corresponder ao conteúdo que foi autorizado. O arquivo foi
        # reserializado, portanto a autorização antiga continua inválida.
        try:
            governanca.preparar_integracao(proposta_path=proposta)
        except ValueError as erro:
            assert str(erro) == "proposta_alterada_apos_autorizacao"
        else:
            raise AssertionError("resserialização não deveria recuperar a autorização")

        # Para o caminho autorizado, restaurar byte a byte o conteúdo que foi
        # originalmente autorizado e recriar apenas o registro de governança.
        proposta.write_bytes(proposta_original)
        (raiz.parent / "governanca" / "integracao-candidato-001.json").unlink()
        autorizada = governanca.autorizar_proposta(
            proposta_path=proposta,
            autorizador="operador_humano",
            motivo="Aprovacao explicita para integrar o candidato.",
        )
        assert autorizada["estado"] == "autorizada"

        preparada = governanca.preparar_integracao(
            proposta_path=proposta,
            branch_integracao="integracao/integracao-candidato-001",
        )
        assert preparada["governanca"]["estado"] == "integracao_preparada"
        assert preparada["governanca"]["integracao"]["baseline_commit"]
        assert preparada["governanca"]["integracao"]["commit_integracao"]
        assert preparada["integracao_executada"] is False
        assert preparada["stable_modificada"] is False
        assert git(raiz, "branch", "--show-current") == "main"
        assert not (raiz / "codigo.py").exists()

        merge_commit = git(
            raiz,
            "rev-parse",
            "refs/heads/integracao/integracao-candidato-001",
        )

        # O teste ainda não está em stable; registrar integração deve bloquear.
        try:
            governanca.registrar_integracao(
                proposta_id="integracao-candidato-001",
                merge_commit=merge_commit,
            )
        except RuntimeError as erro:
            assert "merge-base --is-ancestor" in str(erro)
        else:
            raise AssertionError(
                "integracao ficticia foi aceita"
            )

        git(raiz, "switch", "main")
        git(
            raiz,
            "merge",
            "--ff-only",
            "integracao/integracao-candidato-001",
        )
        merge_commit = git(raiz, "rev-parse", "HEAD")

        integrada = governanca.registrar_integracao(
            proposta_id="integracao-candidato-001",
            merge_commit=merge_commit,
        )
        assert integrada["estado"] == "integrada"
        assert integrada["integracao_executada"] is True
        assert integrada["stable_modificada"] is True

        rollback_base = git(raiz, "rev-parse", "HEAD")
        git(
            raiz,
            "revert",
            "--no-edit",
            rollback_base,
        )
        rollback_commit = git(raiz, "rev-parse", "HEAD")

        final = governanca.registrar_rollback(
            proposta_id="integracao-candidato-001",
            rollback_commit=rollback_commit,
            motivo="Reverter após validação controlada.",
        )
        assert final["estado"] == "rollback_registrado"
        assert final["rollback"]["rollback_commit"] == rollback_commit
        assert final["stable_modificada"] is True

        consultado = governanca.consultar(
            "integracao-candidato-001"
        )
        assert consultado["estado"] == "rollback_registrado"
        assert len(consultado["historico_estados"]) == 5

        print("AUTORIZACAO_EXPLICITA=OK")
        print("INTEGRIDADE_PROPOSTA=OK")
        print("INTEGRACAO_PREPARADA=OK")
        print("STABLE_BLOQUEADA_ATE_MERGE=OK")
        print("INTEGRACAO_REGISTRADA=OK")
        print("ROLLBACK_REGISTRADO=OK")
        print("AUDITORIA_ESTADOS=OK")
        print("SEM_EXECUCAO_AUTOMATICA=OK")
        print("PASSOU: True")


if __name__ == "__main__":
    executar()
