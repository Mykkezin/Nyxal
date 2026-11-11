#!/usr/bin/env python3
"""Regressões para garantir que todos os cristais respeitem NYXAL_STATE_DIR."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROBE = """
import json
import gerenciador_cristal as g
import cristalizacao
import ciclo_cristalizacao

print(json.dumps({
    "binario": str(g.ARQUIVO),
    "legado": str(g.ARQUIVO_LEGADO),
    "backups": str(g.BACKUP_DIR),
    "semantico": str(cristalizacao.ARQUIVO),
    "ciclo": str(ciclo_cristalizacao.ARQUIVO_CRISTAL),
}, ensure_ascii=False))
"""


def executar_probe(raiz: Path, variaveis: dict[str, str]) -> dict[str, str]:
    ambiente = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(raiz / "home"),
        "PYTHONPATH": str(BASE_DIR),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    ambiente.update(variaveis)

    processo = subprocess.run(
        [sys.executable, "-B", "-c", PROBE],
        cwd=str(raiz),
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if processo.returncode != 0:
        raise AssertionError(
            "Probe de caminhos falhou.\n"
            f"stdout:\n{processo.stdout}\n"
            f"stderr:\n{processo.stderr}"
        )
    return json.loads(processo.stdout.strip())


class TestIsolamentoCaminhosCristal(unittest.TestCase):
    def test_state_dir_redireciona_todos_os_cristais(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nyxal-cristal-state-") as tmp:
            raiz = Path(tmp)
            state = raiz / "state"
            caminhos = executar_probe(raiz, {"NYXAL_STATE_DIR": str(state)})

            esperados = {
                "binario": state / "memoria/cristal/cristal.bin",
                "legado": state / "experimentos/cristal_gerenciador.bin",
                "backups": state / "memoria/backups",
                "semantico": state / "memoria/cristalizacao.json",
                "ciclo": state / "memoria/cristal_atual.json",
            }
            for nome, esperado in esperados.items():
                self.assertEqual(Path(caminhos[nome]), esperado.resolve(), nome)

            self.assertFalse(state.exists(), "Importar módulos não deve criar o estado.")

    def test_overrides_especificos_prevalecem_sobre_state_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nyxal-cristal-overrides-") as tmp:
            raiz = Path(tmp)
            state = raiz / "state"
            overrides = {
                "NYXAL_STATE_DIR": str(state),
                "NYXAL_CRISTAL_ARQUIVO": str(raiz / "custom/estrutural.bin"),
                "NYXAL_CRISTAL_LEGADO": str(raiz / "custom/legado.bin"),
                "NYXAL_CRISTAL_BACKUPS": str(raiz / "custom/backups"),
                "NYXAL_CRISTALIZACAO_ARQUIVO": str(raiz / "custom/semantico.json"),
                "NYXAL_CRISTAL_CICLO_ARQUIVO": str(raiz / "custom/ciclo.json"),
            }
            caminhos = executar_probe(raiz, overrides)

            for nome, variavel in (
                ("binario", "NYXAL_CRISTAL_ARQUIVO"),
                ("legado", "NYXAL_CRISTAL_LEGADO"),
                ("backups", "NYXAL_CRISTAL_BACKUPS"),
                ("semantico", "NYXAL_CRISTALIZACAO_ARQUIVO"),
                ("ciclo", "NYXAL_CRISTAL_CICLO_ARQUIVO"),
            ):
                self.assertEqual(
                    Path(caminhos[nome]),
                    Path(overrides[variavel]).resolve(),
                    variavel,
                )

    def test_sem_state_dir_preserva_caminhos_legados_do_projeto(self) -> None:
        caminhos = executar_probe(Path(tempfile.gettempdir()), {})
        esperados = {
            "binario": BASE_DIR / "memoria/cristal/cristal.bin",
            "legado": BASE_DIR / "experimentos/cristal_gerenciador.bin",
            "backups": BASE_DIR / "memoria/backups",
            "semantico": BASE_DIR / "memoria/cristalizacao.json",
            "ciclo": BASE_DIR / "memoria/cristal_atual.json",
        }
        for nome, esperado in esperados.items():
            self.assertEqual(Path(caminhos[nome]), esperado.resolve(), nome)


if __name__ == "__main__":
    unittest.main()
