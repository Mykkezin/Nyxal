#!/usr/bin/env python3
"""Prova end-to-end do laboratório remoto da Nyxal.

Requer:
    NYXAL_GITHUB_TOKEN

O teste cria uma branch experimento/* temporária, dispara o workflow
confiável no GitHub Actions, recupera o result.json pelos logs e remove
a branch experimental ao final.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from nixal_laboratorio_remoto import LaboratorioRemotoNixal


def main() -> int:
    if not os.environ.get("NYXAL_GITHUB_TOKEN", "").strip():
        print("SKIP: defina NYXAL_GITHUB_TOKEN para executar o E2E remoto.")
        return 0

    laboratorio = LaboratorioRemotoNixal()

    experimento_id = (
        "e2e-"
        + time.strftime("%Y%m%d%H%M%S")
        + "-"
        + str(time.time_ns())[-6:]
    )

    branch = laboratorio.branch_experimento(
        experimento_id
    )

    with tempfile.TemporaryDirectory(
        prefix="nyxal-e2e-"
    ) as diretorio:
        origem = Path(diretorio) / "main.py"
        origem.write_text(
            "print('NYXAL_REMOTE_LAB_E2E_OK')\n",
            encoding="utf-8",
        )

        publicado = False
        concluido = False

        try:
            publicado_resultado = (
                laboratorio.publicar_experimento(
                    experimento_id=experimento_id,
                    arquivo_origem=origem,
                    descricao=(
                        "Prova E2E do laboratorio remoto da Nyxal."
                    ),
                    timeout_seconds=30,
                )
            )
            publicado = True

            assert (
                publicado_resultado["estado"]
                == "experimento_publicado"
            )
            assert publicado_resultado["branch"] == branch
            assert len(
                publicado_resultado["commit_sha"]
            ) == 40
            assert (
                publicado_resultado["stable_modificada"]
                is False
            )

            disparo = laboratorio.disparar_workflow(
                experimento_id=experimento_id,
                experiment_ref=branch,
                expected_sha=(
                    publicado_resultado["commit_sha"]
                ),
            )

            assert (
                disparo["estado"]
                == "workflow_disparado"
            )

            resultado = laboratorio.aguardar_resultado(
                experimento_id=experimento_id,
                timeout_segundos=300,
                intervalo_segundos=5,
            )

            assert resultado is not None, (
                "workflow não retornou estado"
            )
            assert (
                resultado.get("estado")
                == "resultado_recuperado"
            ), resultado

            laboratorio_resultado = resultado["resultado"]

            assert (
                laboratorio_resultado["experimento_id"]
                == experimento_id
            )
            assert (
                laboratorio_resultado["experiment_sha"]
                == publicado_resultado["commit_sha"]
            )
            assert (
                laboratorio_resultado["status"]
                == "sucesso"
            ), laboratorio_resultado
            assert (
                laboratorio_resultado["experimento_sucesso"]
                is True
            )
            assert (
                laboratorio_resultado["exit_code"]
                == 0
            )
            assert (
                laboratorio_resultado["stable_modificada"]
                is False
            )
            assert (
                laboratorio_resultado["autorizacao_explicita"]
                is False
            )

            print("=" * 60)
            print("TESTE E2E — NYXAL REMOTE LAB")
            print("=" * 60)
            print("BRANCH_PUBLICADA=OK")
            print("WORKFLOW_DISPARADO=OK")
            print("RUNNER_REMOTO=OK")
            print("RESULTADO_RECUPERADO=OK")
            print("SHA_VALIDADO=OK")
            print("EXPERIMENTO_SUCESSO=OK")
            print("STABLE_MODIFICADA=FALSE")
            print("AUTORIZACAO_EXPLICITA=FALSE")
            print("PASSOU: True")
            print("=" * 60)
            concluido = True

        finally:
            if publicado and concluido:
                try:
                    laboratorio.remover_branch_experimento(
                        branch
                    )
                except Exception as erro:
                    print(
                        "AVISO: não foi possível remover "
                        f"a branch {branch}: {type(erro).__name__}: {erro}"
                    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
