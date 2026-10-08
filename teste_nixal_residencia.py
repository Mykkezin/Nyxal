#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from nixal_residencia import ResidenciaNyxOS

class ResidenciaNyxOSTest(unittest.TestCase):
    def test_snapshot_somente_leitura(self) -> None:
        with patch("nixal_residencia.shutil.which", return_value="/usr/bin/systemctl"):
            residencia = ResidenciaNyxOS()
        resposta = subprocess.CompletedProcess(
            args=["systemctl"],
            returncode=0,
            stdout=(
                "Description=NyxOS — ciclo operacional residente\n"
                "ActiveState=active\n"
                "SubState=running\n"
                "MainPID=1234\n"
                "UnitFileState=enabled\n"
                "MemoryCurrent=104857600\n"
            ),
            stderr="",
        )
        with patch("nixal_residencia.subprocess.run", return_value=resposta):
            snapshot = residencia.snapshot()

        self.assertTrue(snapshot["sucesso"])
        self.assertEqual(snapshot["modo"], "somente_leitura")
        self.assertEqual(len(snapshot["unidades"]), 5)
        self.assertEqual(snapshot["unidades"][0]["status"], "active")
        self.assertEqual(snapshot["unidades"][0]["subState"], "running")
        self.assertEqual(snapshot["unidades"][0]["pid"], 1234)
        self.assertTrue(snapshot["unidades"][0]["enabled"])

if __name__ == "__main__":
    unittest.main()
