#!/usr/bin/env python3
"""Prova do ciclo de evolução controlada com integração e rollback isolados."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from nixal_evolucao_controlada import EvolucaoControladaNixal


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "git_falhou")
    return r.stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-b", "main")
        git(repo, "config", "user.name", "Nyxal Test")
        git(repo, "config", "user.email", "nyxal-test@example.invalid")

        base = repo / "baseline.py"
        base.write_text("BASELINE = True\n", encoding="utf-8")
        git(repo, "add", "baseline.py")
        git(repo, "commit", "-m", "baseline")
        baseline_sha = git(repo, "rev-parse", "HEAD")

        experimento = repo / "experimento"
        experimento.mkdir()
        candidato = experimento / "melhoria.py"
        candidato.write_text(
            "def melhoria():\n    return 'candidato-validado'\n",
            encoding="utf-8",
        )

        manifesto = json.dumps(
            {
                "versao_contrato": 1,
                "nome": "melhoria_controlada",
                "objetivo": "provar evolucao controlada",
                "tipo": "python",
                "arquivo": "melhoria.py",
                "operacoes_permitidas": ["analise", "py_compile"],
                "executar": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        (experimento / "manifesto.json").write_text(
            manifesto, encoding="utf-8"
        )

        ciclo = EvolucaoControladaNixal(repo).executar_ciclo(
            ciclo_id="evolucao-01",
            arquivo=candidato,
            manifesto=manifesto,
            contrato=json.loads(manifesto),
            experimento_raiz=experimento,
            autorizar_integracao=True,
            stable="main",
        )

        assert ciclo["sucesso"] is True, ciclo
        assert ciclo["estado"] == "integracao_preparada", ciclo
        assert ciclo["avaliacao"]["aprovado"] is True, ciclo
        assert ciclo["integracao"]["stable_modificada"] is False, ciclo

        branch = ciclo["integracao"]["branch_integracao"]
        integration_sha = ciclo["integracao"]["commit_integracao"]
        assert git(repo, "branch", "--show-current") == branch
        assert Path(ciclo["integracao"]["arquivo_integrado"]).exists()

        # A integração foi preparada em branch separada; agora simulamos
        # a rejeição do candidato e voltamos ao baseline sem tocar main.
        rollback = EvolucaoControladaNixal.rollback(repo, "main")
        assert rollback["branch_atual"] == "main", rollback
        assert git(repo, "rev-parse", "HEAD") == baseline_sha
        assert not (repo / "melhoria.py").exists()
        assert git(repo, "status", "--porcelain") == ""

        print("TESTE_EVOLUCAO_CONTROLADA_NYXAL_OK")
        print(f"BASELINE={baseline_sha}")
        print(f"INTEGRATION_COMMIT={integration_sha}")
        print(f"ROLLBACK_BRANCH={rollback['branch_atual']}")
        print("STABLE_PRESERVADA=OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
