#!/usr/bin/env python3
from __future__ import annotations

import unittest
from unittest.mock import patch

from nixal_observabilidade_sistema import ObservabilidadeSistemaNixOS


class TestObservabilidadeSistema(unittest.TestCase):
    def test_snapshot_explicita_modo_somente_leitura(self):
        with (
            patch("nixal_observabilidade_sistema.shutil.disk_usage", return_value=type("Usage", (), {
                "total": 1000, "used": 400, "free": 600
            })()),
            patch.object(ObservabilidadeSistemaNixOS, "_memoria", return_value={"uso_percentual": 50.0}),
            patch.object(ObservabilidadeSistemaNixOS, "_processos", return_value={"total_observado": 3, "top_cpu": []}),
            patch.object(ObservabilidadeSistemaNixOS, "_servicos", return_value={"estado": "observado", "unidades": []}),
            patch("nixal_observabilidade_sistema.os.getloadavg", return_value=(0.1, 0.2, 0.3)),
        ):
            result = ObservabilidadeSistemaNixOS().snapshot()

        self.assertTrue(result["sucesso"])
        self.assertEqual(result["modo"], "somente_leitura")
        self.assertFalse(result["governanca"]["comandos_arbitrarios_habilitados"])
        self.assertFalse(result["governanca"]["alteracao_de_arquivos_habilitada"])
        self.assertFalse(result["governanca"]["controle_de_servicos_habilitado"])
        self.assertEqual(result["armazenamento_home"]["uso_percentual"], 40.0)

    def test_servicos_usa_consulta_fixa(self):
        class Completed:
            returncode = 0
            stdout = "example.service loaded active running Description here\n"
            stderr = ""

        with patch("nixal_observabilidade_sistema.subprocess.run", return_value=Completed()) as run:
            result = ObservabilidadeSistemaNixOS._servicos(user=True)

        args = run.call_args.args[0]
        self.assertEqual(args[0:2], ["systemctl", "--user"])
        self.assertIn("list-units", args)
        self.assertIn("--no-pager", args)
        self.assertNotIn("shell", args)
        self.assertEqual(result["unidades"][0]["unidade"], "example.service")


if __name__ == "__main__":
    unittest.main(verbosity=2)
