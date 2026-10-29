#!/usr/bin/env python3
"""Testes isolados do preflight Fase 1; só usam diretórios temporários."""
from __future__ import annotations

import hashlib
import importlib.util
import os
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "ops" / "nyxal_preflight_fase1.py"
SPEC = importlib.util.spec_from_file_location("nyxal_preflight_fase1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class TesteNyxalPreflightFase1(unittest.TestCase):
    def test_cristal_nxcm_v1_com_tripla_valida(self):
        raw = (
            b"NXCM\x01"
            + b"\x01\x01A"
            + b"\x02\x01r"
            + b"\x03\x01\x00\x00\x00"
        )
        result = PREFLIGHT.parse_crystal(raw)
        self.assertEqual(result["versao"], 1)
        self.assertEqual(result["conceitos"], 1)
        self.assertEqual(result["relacoes"], 1)
        self.assertEqual(result["triplas"], 1)

    def test_cristal_invalido_falha_fechado(self):
        cases = (
            b"NOPE\x01",
            b"NXCM\x03",
            b"NXCM\x01\x01\x04A",
            b"NXCM\x01\x07",
            b"NXCM\x01\x03\x01\x00\x00\x00",
        )
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(PREFLIGHT.PreflightError):
                    PREFLIGHT.parse_crystal(raw)

    def test_json_com_chave_duplicada_e_rejeitado(self):
        with self.assertRaises(PREFLIGHT.PreflightError):
            PREFLIGHT.strict_json(b'{"versao":1,"versao":2}')

    def test_archive_manifesto_e_hashes_conferem(self):
        with tempfile.TemporaryDirectory() as temporary:
            backup = Path(temporary)
            payload_name = "payload/repo_state/eventos.json"
            content = b'{"eventos":[]}\n'
            archive = backup / "estado_vivo.tar.gz"
            manifest = backup / "manifesto_hashes.txt"
            checksum = backup / "estado_vivo.tar.gz.sha256"

            import io
            import tarfile
            info = tarfile.TarInfo(payload_name)
            info.size = len(content)
            with tarfile.open(archive, "w:gz") as tar:
                tar.addfile(info, io.BytesIO(content))

            member_hash = hashlib.sha256(content).hexdigest()
            manifest.write_text(f"{member_hash}  {payload_name}\n", encoding="utf-8")
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            checksum.write_text(f"{archive_hash}  estado_vivo.tar.gz\n", encoding="utf-8")

            summary = PREFLIGHT.verify_backup(backup, archive_hash)
            self.assertEqual(summary["arquivos"], 1)
            with self.assertRaises(PREFLIGHT.PreflightError):
                PREFLIGHT.verify_backup(backup, "0" * 64)

            checksum.write_text(f"{'0' * 64}  estado_vivo.tar.gz\n", encoding="utf-8")
            with self.assertRaises(PREFLIGHT.PreflightError):
                PREFLIGHT.verify_backup(backup, archive_hash)

    def test_manifesto_nao_aceita_travessia_de_caminho(self):
        with tempfile.TemporaryDirectory() as temporary:
            backup = Path(temporary)
            archive = backup / "estado_vivo.tar.gz"
            manifest = backup / "manifesto_hashes.txt"
            checksum = backup / "estado_vivo.tar.gz.sha256"
            import io
            with tarfile.open(archive, "w:gz") as tar:
                payload = b"x"
                info = tarfile.TarInfo("payload/file")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            checksum.write_text(f"{archive_hash}  estado_vivo.tar.gz\n", encoding="utf-8")
            manifest.write_text(f"{'0' * 64}  payload/../outside\n", encoding="utf-8")
            with self.assertRaises(PREFLIGHT.PreflightError):
                PREFLIGHT.verify_backup(backup, archive_hash)

    def test_cadeia_de_aprovacao_valida(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "aprovacoes.jsonl"
            record = {
                "previous_hash": PREFLIGHT.GENESIS_HASH,
                "tipo": "aprovacao_registrada",
                "aprovacao_id": "teste_1",
                "observado_em": "2026-10-29T00:00:00+00:00",
                "valor": {"tipo": "simulacao", "escopo": "teste"},
            }
            record["entry_hash"] = hashlib.sha256(
                PREFLIGHT.canonical_json(record)
            ).hexdigest()
            path.write_bytes(PREFLIGHT.canonical_json(record) + b"\n")
            path.chmod(0o600)
            result = PREFLIGHT.check_hash_chain(path, "approval", os.getuid())
            self.assertEqual(result["registros"], 1)

    def test_cadeia_de_aprovacao_corrompida_e_rejeitada(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "aprovacoes.jsonl"
            record = {
                "previous_hash": PREFLIGHT.GENESIS_HASH,
                "tipo": "aprovacao_registrada",
                "aprovacao_id": "teste_1",
                "observado_em": "2026-10-29T00:00:00+00:00",
                "valor": {"tipo": "simulacao", "escopo": "teste"},
                "entry_hash": "0" * 64,
            }
            path.write_bytes(PREFLIGHT.canonical_json(record) + b"\n")
            path.chmod(0o600)
            with self.assertRaises(PREFLIGHT.PreflightError):
                PREFLIGHT.check_hash_chain(path, "approval", os.getuid())

    def test_script_nao_invoca_modulos_de_runtime_ou_mutacoes(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotRegex(
            source,
            r"(?m)^\s*import\s+(gerenciador_cristal|nixal_delta|nixal_memoria_conversacional)\b",
        )
        for forbidden in (
            "systemctl\", \"stop",
            "systemctl\", \"restart",
            "os.replace(",
            ".write_text(",
            ".unlink(",
            ".mkdir(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
