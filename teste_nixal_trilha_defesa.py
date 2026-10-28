#!/usr/bin/env python3
"""Testes de integridade, limites e caminhos seguros da trilha de defesa."""
from __future__ import annotations

import os
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nixal_trilha_defesa import RegistroTrilhaDefesa, TrilhaDefesaError


def sinal(origem_ip: str = "203.0.113.7") -> dict:
    return {
        "tipo_evento": "falha_autenticacao",
        "fonte_sinal": "api-auth",
        "origem_ip": origem_ip,
        "severidade": "alta",
    }


def plano(plano_id: str = "plano-" + "a" * 24) -> dict:
    return {
        "plano_id": plano_id,
        "tipo": "bloqueio_temporario_origem",
        "escopo": "203.0.113.7",
        "estado": "aguardando_aprovacao",
        "modo": "dry_run",
        "aprovacao_verificada": False,
        "duracao_segundos": 300,
    }


class TesteTrilhaDefesa(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nyxal-defense-audit-")
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.arquivo = self.raiz / "estado" / "defesa.jsonl"
        self.trilha = RegistroTrilhaDefesa(self.arquivo)

    def test_registros_sao_persistidos_com_cadeia_verificavel(self) -> None:
        primeiro = self.trilha.registrar("sinal_observado", sinal())
        segundo = self.trilha.registrar("plano_preparado", plano())

        self.assertEqual(primeiro["sequencia"], 1)
        self.assertEqual(segundo["sequencia"], 2)
        self.assertEqual(segundo["hash_anterior"], primeiro["hash"])
        self.assertEqual(stat.S_IMODE(self.arquivo.stat().st_mode), 0o600)

        valida = RegistroTrilhaDefesa(self.arquivo).validar()
        self.assertTrue(valida["valido"])
        self.assertEqual(valida["registros"], 2)
        self.assertEqual(valida["ultimo_hash"], segundo["hash"])
        self.assertTrue(self.trilha.contexto()["auditoria_duravel"])

        texto = self.arquivo.read_text(encoding="utf-8")
        self.assertNotIn("Authorization", texto)
        self.assertNotIn("Bearer ", texto)
        self.assertNotIn("token=", texto)
        self.assertNotIn("motivo", texto)

    def test_campos_desconhecidos_ou_segredos_sao_rejeitados_sem_gravacao(self) -> None:
        entrada = sinal()
        entrada["token"] = "SEGREDO-QUE-NAO-PODE-PERSISTIR"
        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar("sinal_observado", entrada)
        self.assertFalse(self.arquivo.exists())

        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar(
                "sinal_observado",
                {"tipo_evento": "falha_autenticacao", "fonte_sinal": "cliente"},
            )
        self.assertFalse(self.arquivo.exists())

    def test_evento_e_identificadores_fora_do_esquema_sao_rejeitados(self) -> None:
        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar("comando_shell", sinal())
        dados = plano()
        dados["escopo"] = "../../etc/passwd"
        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar("plano_preparado", dados)
        self.assertFalse(self.arquivo.exists())

    def test_symlink_no_diretorio_pai_e_rejeitado(self) -> None:
        fora = self.raiz / "fora"
        fora.mkdir()
        link = self.raiz / "atalho"
        link.symlink_to(fora, target_is_directory=True)
        arquivo_linkado = RegistroTrilhaDefesa(link / "defesa.jsonl")

        with self.assertRaises(TrilhaDefesaError):
            arquivo_linkado.registrar("sinal_observado", sinal())
        self.assertEqual(list(fora.iterdir()), [])

    def test_symlink_no_arquivo_nao_modifica_destino(self) -> None:
        fora = self.raiz / "evidencia.txt"
        fora.write_text("preservar-evidencia\n", encoding="utf-8")
        os.chmod(fora, 0o600)
        self.arquivo.parent.mkdir()
        self.arquivo.symlink_to(fora)

        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar("sinal_observado", sinal())
        self.assertEqual(fora.read_text(encoding="utf-8"), "preservar-evidencia\n")

    def test_symlink_no_arquivo_lock_nao_modifica_destino(self) -> None:
        self.arquivo.parent.mkdir()
        fora = self.raiz / "lock-destino.txt"
        fora.write_text("lock original\n", encoding="utf-8")
        os.chmod(fora, 0o600)
        self.arquivo.with_name(self.arquivo.name + ".lock").symlink_to(fora)

        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar("sinal_observado", sinal())
        self.assertEqual(fora.read_text(encoding="utf-8"), "lock original\n")
        self.assertFalse(self.arquivo.exists())

    def test_json_corrompido_e_preservado_e_bloqueia_novas_gravacoes(self) -> None:
        self.arquivo.parent.mkdir()
        original = b'{"registro":"corrompido"}\n'
        self.arquivo.write_bytes(original)
        os.chmod(self.arquivo, 0o600)

        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar("sinal_observado", sinal())
        self.assertEqual(self.arquivo.read_bytes(), original)
        self.assertFalse(self.trilha.contexto()["auditoria_duravel"])

        with self.assertRaises(TrilhaDefesaError):
            self.trilha.registrar("sinal_observado", sinal("203.0.113.8"))
        self.assertEqual(self.arquivo.read_bytes(), original)

    def test_permissao_publica_nao_e_aceita(self) -> None:
        self.trilha.registrar("sinal_observado", sinal())
        os.chmod(self.arquivo, 0o644)
        outro = RegistroTrilhaDefesa(self.arquivo)
        estado = outro.validar()
        self.assertFalse(estado["valido"])
        self.assertEqual(stat.S_IMODE(self.arquivo.stat().st_mode), 0o644)

    def test_limite_de_bytes_falha_sem_truncar_registros_validos(self) -> None:
        trilha = RegistroTrilhaDefesa(
            self.arquivo,
            max_bytes=1024,
            max_registros=100,
        )
        completou = 0
        while True:
            try:
                trilha.registrar("sinal_observado", sinal(f"203.0.113.{(completou % 200) + 1}"))
                completou += 1
            except TrilhaDefesaError:
                break
            self.assertLess(completou, 100, "o limite em bytes deveria ser atingido")

        self.assertGreater(completou, 0)
        bytes_anteriores = self.arquivo.read_bytes()
        self.assertLessEqual(len(bytes_anteriores), 1024)
        self.assertTrue(RegistroTrilhaDefesa(self.arquivo, max_bytes=1024).validar()["valido"])
        with self.assertRaises(TrilhaDefesaError):
            trilha.registrar("sinal_observado", sinal("203.0.113.200"))
        self.assertEqual(self.arquivo.read_bytes(), bytes_anteriores)

    def test_concorrencia_preserva_sequencia_e_hashes(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(
                lambda indice: self.trilha.registrar(
                    "sinal_observado",
                    sinal(f"203.0.113.{(indice % 200) + 1}"),
                ),
                range(32),
            ))

        resultado = RegistroTrilhaDefesa(self.arquivo).validar()
        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["registros"], 32)

    def test_limite_de_registros_nao_descarta_historico(self) -> None:
        trilha = RegistroTrilhaDefesa(self.arquivo, max_registros=1)
        trilha.registrar("sinal_observado", sinal())
        original = self.arquivo.read_bytes()

        with self.assertRaises(TrilhaDefesaError):
            trilha.registrar("sinal_observado", sinal("203.0.113.8"))
        self.assertEqual(self.arquivo.read_bytes(), original)
        self.assertTrue(RegistroTrilhaDefesa(self.arquivo, max_registros=1).validar()["valido"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
