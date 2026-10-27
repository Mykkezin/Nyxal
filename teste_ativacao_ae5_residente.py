#!/usr/bin/env python3
"""Fast structural checks for governed AE5 activation in the resident service.

These checks intentionally use only the Python standard library. They validate
wiring and guardrails, not execution on the user's physical machine.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class TestAE5ResidentActivation(unittest.TestCase):
    def test_systemd_enables_ae5_only_for_resident_service(self) -> None:
        resident = read("deploy/systemd/nyxos-residente.service")
        api = read("deploy/systemd/nyxal-api.service")

        resident_exec = next(
            line for line in resident.splitlines()
            if line.startswith("ExecStart=")
        )
        self.assertIn("--habilitar-ae5-descoberta", resident_exec)
        self.assertNotIn("--habilitar-ae5-descoberta", api)

    def test_launcher_defines_and_injects_flag(self) -> None:
        launcher = read("executar_nyxos_residente.py")
        self.assertIn('"--habilitar-ae5-descoberta"', launcher)
        self.assertGreaterEqual(
            launcher.count("habilitada=args.habilitar_ae5_descoberta"),
            2,
            "AE5 discovery and the dual dataset collector should share the explicit flag",
        )

    def test_resident_wires_ae4_to_ae5_and_dataset_collector(self) -> None:
        resident = read("nixal_ciclo_residente.py")
        self.assertIn("self.ciclo_evolucao_ae4.processar_ciclo(resultado)", resident)
        self.assertIn("self.descoberta_continua_ae5.processar(", resident)
        self.assertIn("self.coletor_dataset_dual_ae5.processar_ciclo(", resident)
        self.assertIn("ae4_resultado=auto_evolucao_ae4_resultado", resident)

    def test_dataset_is_outside_git_and_not_trained_or_deployed_automatically(self) -> None:
        collector = read("nixal_coletor_dataset_dual_ae5.py")
        self.assertIn('"Nyxal-datasets"', collector)
        self.assertIn('"treinamento_automatico": False', collector)
        self.assertIn('"implantacao_automatica": False', collector)
        self.assertIn('"causalidade_comprovada": False', collector)

    def test_evolution_gates_remain_explicit(self) -> None:
        ae2 = read("nixal_auto_experimento_ae2.py")
        ae4 = read("nixal_ciclo_evolucao_ae4.py")
        self.assertIn("self.max_por_ciclo = max_por_ciclo", ae2)
        self.assertIn('"retry_automatico": False', ae4)
        self.assertIn('"stable_modificada": False', ae4)
        self.assertIn('"autorizacao_explicita": False', ae4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
