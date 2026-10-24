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


if __name__ == "__main__":
    unittest.main()
