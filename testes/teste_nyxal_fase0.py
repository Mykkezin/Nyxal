#!/usr/bin/env python3
"""Contratos estáticos de segurança da ferramenta de salvaguarda Fase 0."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "deploy" / "ops" / "nyxal_fase0.sh"
CONTEUDO = SCRIPT.read_text(encoding="utf-8")


class TesteNyxalFase0(unittest.TestCase):
    def test_sintaxe_bash(self):
        resultado = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            resultado.returncode,
            0,
            msg=resultado.stderr or resultado.stdout,
        )

    def test_usa_o_systemd_do_usuario_real(self):
        self.assertIn("systemctl --user", CONTEUDO)
        self.assertIn("nyxal-api.service", CONTEUDO)
        self.assertIn("nyxos-residente.service", CONTEUDO)
        self.assertIn(".config/systemd/user", CONTEUDO)
        self.assertIn("SUDO_USER", CONTEUDO)

    def test_backup_tem_manifesto_hash_e_rehearsal(self):
        self.assertIn("estado_vivo.tar.gz", CONTEUDO)
        self.assertIn("estado_vivo.tar.gz.sha256", CONTEUDO)
        self.assertIn("manifesto_hashes.txt", CONTEUDO)
        self.assertIn("sha256sum -c", CONTEUDO)
        self.assertIn("restore-rehearsal", CONTEUDO)

    def test_nomes_dos_modulos_correspondem_ao_repositorio(self):
        for nome in (
            "gerenciador_cristal.py",
            "nixal_delta.py",
            "nixal_aprovacao_defesa.py",
            "nixal_auditoria_defesa.py",
            "nixal_memoria_conversacional.py",
            "nixal_persistencia_operacional.py",
            "nixal_executor_defesa_governada.py",
            "nyxal_web_api.py",
        ):
            with self.subTest(nome=nome):
                self.assertIn(nome, CONTEUDO)

        self.assertNotIn("nixal_cristal.py", CONTEUDO)
        self.assertNotIn("nixal_approval.py", CONTEUDO)
        self.assertNotIn("nixal_conversation_memory.py", CONTEUDO)

    def test_nao_faz_pull_nem_quarentena_automatica_de_estado(self):
        self.assertNotIn("git pull ", CONTEUDO)
        self.assertNotIn('mv "$REPO_DIR/eventos_delta_nyxos.json"', CONTEUDO)
        self.assertNotIn("quarentenar_cristal(", CONTEUDO)

    def test_valores_de_environment_sao_redigidos_no_diff(self):
        self.assertIn("REDACTED_ENVIRONMENT_LINE", CONTEUDO)
        self.assertIn("Conteúdo de arquivos .env/segredos não foi impresso", CONTEUDO)


if __name__ == "__main__":
    unittest.main()
