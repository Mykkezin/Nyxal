#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nixal_trilha_http import RegistroTrilhaHTTP


class TestRegistroTrilhaHTTP(unittest.TestCase):
    def test_registra_metadados_sem_query_string(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "traces.jsonl"
            trilha = RegistroTrilhaHTTP(caminho)
            registro = trilha.registrar(
                request_id="req-test-1", method="GET",
                path="/api/public/status?token=nao-persistir&email=secreto@example.com",
                status_code=200, duration_ms=12.34567,
            )
            self.assertEqual(registro["route"], "/api/public/status")
            self.assertEqual(registro["outcome"], "success")
            texto = caminho.read_text(encoding="utf-8")
            self.assertNotIn("token", texto)
            self.assertNotIn("secreto@example.com", texto)
            dados = json.loads(texto)
            self.assertNotIn("body", dados)
            self.assertNotIn("prompt", dados)
            self.assertEqual(dados["duration_ms"], 12.346)

    def test_classifica_status_e_registra_apenas_tipo_de_excecao(self):
        with tempfile.TemporaryDirectory() as diretorio:
            trilha = RegistroTrilhaHTTP(Path(diretorio) / "traces.jsonl")
            casos = [(204, None, "success"), (404, None, "client_error"),
                     (503, None, "server_error"), (200, "RuntimeError", "exception")]
            resultados = [
                trilha.registrar(request_id=f"r{i}", method="POST", path="/api/chat",
                                 status_code=status, duration_ms=1, error_type=erro)
                for i, (status, erro, _) in enumerate(casos)
            ]
            self.assertEqual([r["outcome"] for r in resultados], [c[2] for c in casos])
            texto = Path(diretorio, "traces.jsonl").read_text(encoding="utf-8")
            self.assertIn("RuntimeError", texto)
            self.assertNotIn("password", texto)

    def test_desativado_nao_escreve(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "traces.jsonl"
            trilha = RegistroTrilhaHTTP(caminho, habilitado=False)
            self.assertIsNone(trilha.registrar(request_id="r", method="GET",
                                               path="/health", status_code=200,
                                               duration_ms=0))
            self.assertFalse(caminho.exists())

    def test_rotacao_limita_o_historico(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "traces.jsonl"
            trilha = RegistroTrilhaHTTP(caminho, max_bytes=1024, backups=1)
            for i in range(12):
                trilha.registrar(request_id=f"request-{i}", method="GET",
                                 path="/api/public/status", status_code=200,
                                 duration_ms=1)
            self.assertTrue(caminho.exists())
            self.assertTrue(caminho.with_name("traces.jsonl.1").exists())
            self.assertLessEqual(caminho.stat().st_size, 1024)
            self.assertLessEqual(caminho.with_name("traces.jsonl.1").stat().st_size, 1024)

    def test_configuracao_invalida_e_rejeitada(self):
        with tempfile.TemporaryDirectory() as diretorio:
            with self.assertRaises(ValueError):
                RegistroTrilhaHTTP(Path(diretorio) / "x.jsonl", max_bytes=10)
            with self.assertRaises(ValueError):
                RegistroTrilhaHTTP(Path(diretorio) / "x.jsonl", backups=99)


if __name__ == "__main__":
    unittest.main(verbosity=2)
