#!/usr/bin/env python3
"""Regressões para impedir crescimento ilimitado dos logs operacionais."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nixal_capacidades
import nixal_runtime
from nixal_capacidades import GerenciadorCapacidades, ResultadoCapacidade


class TestLimitesArmazenamento(unittest.TestCase):
    def test_log_capacidades_respeita_limite_em_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            base = Path(diretorio)
            caminho_log = base / "log_capacidades_nixal.json"
            caminho_capacidades = base / "capacidades_nixal.json"

            with (
                patch.object(nixal_capacidades, "ARQUIVO_LOG", caminho_log),
                patch.object(
                    nixal_capacidades,
                    "ARQUIVO_CAPACIDADES",
                    caminho_capacidades,
                ),
            ):
                gerenciador = GerenciadorCapacidades()
                gerenciador._registrar_execucao(
                    ResultadoCapacidade(
                        sucesso=True,
                        capacidade="resultado_grande",
                        resultado={"conteudo": "x" * (
                            nixal_capacidades.MAX_TAMANHO_ARQUIVO * 2
                        )},
                        timestamp=1.0,
                        duracao_ms=1.0,
                    )
                )

            self.assertLessEqual(
                caminho_log.stat().st_size,
                nixal_capacidades.MAX_TAMANHO_ARQUIVO,
            )
            dados = json.loads(caminho_log.read_text(encoding="utf-8"))
            self.assertTrue(dados[-1]["resultado"]["truncado"])

    def test_log_runtime_resume_ciclo_grande_e_respeita_limite(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_log = Path(diretorio) / "log_nyxal_runtime.json"
            runtime = object.__new__(nixal_runtime.NyxalRuntime)
            runtime.arquivo_log = caminho_log

            ciclo = {
                "sucesso": True,
                "estado": "ciclo_concluido",
                "origem": "teste",
                "versao_runtime": "teste",
                "ciclo_id": "ciclo-grande",
                "iniciado_em": "inicio",
                "concluido_em": "fim",
                "valor": {"etapas": [{"conteudo": "x" * (
                    nixal_runtime.MAX_TAMANHO_LOG_RUNTIME * 2
                )}]},
                "erro": None,
            }
            runtime._registrar_log(ciclo)

            self.assertLessEqual(
                caminho_log.stat().st_size,
                nixal_runtime.MAX_TAMANHO_LOG_RUNTIME,
            )
            dados = json.loads(caminho_log.read_text(encoding="utf-8"))
            self.assertTrue(dados[-1]["valor"]["resumo_truncado"])


    def test_log_capacidades_descarta_historico_preexistente_acima_do_teto(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_log = Path(diretorio) / "log_capacidades_nixal.json"
            registro_antigo = {
                "sucesso": True,
                "capacidade": "registro_antigo",
                "resultado": {"ok": True},
                "erro": None,
                "timestamp": 1.0,
                "duracao_ms": 1.0,
            }
            json_antigo = json.dumps([registro_antigo], separators=(",", ":")).encode("utf-8")
            caminho_log.write_bytes(
                json_antigo[:-1]
                + b" " * (nixal_capacidades.MAX_TAMANHO_ARQUIVO + 64)
                + b"]"
            )
            with patch.object(nixal_capacidades, "ARQUIVO_LOG", caminho_log):
                gerenciador = GerenciadorCapacidades()
                gerenciador._registrar_execucao(
                    ResultadoCapacidade(
                        sucesso=True,
                        capacidade="novo_registro",
                        resultado={"ok": True},
                        timestamp=2.0,
                        duracao_ms=1.0,
                    )
                )

            self.assertLessEqual(
                caminho_log.stat().st_size,
                nixal_capacidades.MAX_TAMANHO_ARQUIVO,
            )
            dados = json.loads(caminho_log.read_text(encoding="utf-8"))
            self.assertEqual(len(dados), 1)
            self.assertEqual(dados[0]["capacidade"], "novo_registro")

    def test_log_runtime_descarta_historico_preexistente_acima_do_teto(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_log = Path(diretorio) / "log_nyxal_runtime.json"
            registro_antigo = {
                "sucesso": True,
                "estado": "ciclo_antigo",
                "origem": "teste",
                "versao_runtime": "teste",
                "ciclo_id": "ciclo-antigo",
                "valor": {"ok": True},
            }
            json_antigo = json.dumps([registro_antigo], separators=(",", ":")).encode("utf-8")
            caminho_log.write_bytes(
                json_antigo[:-1]
                + b" " * (nixal_runtime.MAX_TAMANHO_LOG_RUNTIME + 64)
                + b"]"
            )
            runtime = object.__new__(nixal_runtime.NyxalRuntime)
            runtime.arquivo_log = caminho_log
            ciclo = {
                "sucesso": True,
                "estado": "ciclo_concluido",
                "origem": "teste",
                "versao_runtime": "teste",
                "ciclo_id": "novo-ciclo",
                "iniciado_em": "inicio",
                "concluido_em": "fim",
                "valor": {"ok": True},
                "erro": None,
            }

            runtime._registrar_log(ciclo)

            self.assertLessEqual(
                caminho_log.stat().st_size,
                nixal_runtime.MAX_TAMANHO_LOG_RUNTIME,
            )
            dados = json.loads(caminho_log.read_text(encoding="utf-8"))
            self.assertEqual(len(dados), 1)
            self.assertEqual(dados[0]["ciclo_id"], "novo-ciclo")

    def test_janitor_falha_fechado_quando_a_listagem_de_artefatos_falha(self) -> None:
        workflow_path = Path(".github/workflows/prune-actions-artifacts.yml")
        workflow = workflow_path.read_text(encoding="utf-8")

        # Uma falha do gh api precisa falhar o step, não parecer "zero artefatos".
        self.assertIn('if ! artifact_rows="$(gh api --paginate', workflow)
        self.assertIn('done <<< "$artifact_rows"', workflow)
        self.assertNotIn("done < <(", workflow)

        # A exclusão fica restrita ao nome exato e ao limite de idade explícito.
        self.assertIn(
            'select(.name == "nyxal-projeto-nivel10" and .expired == false)',
            workflow,
        )
        self.assertIn('if [[ "$created_epoch" -lt "$cutoff_epoch" ]]; then', workflow)
        self.assertIn(
            '"repos/${GITHUB_REPOSITORY}/actions/artifacts/${artifact_id}"',
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
