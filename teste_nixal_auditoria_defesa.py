#!/usr/bin/env python3
"""Testes de integridade, limites e privacidade da trilha de defesa."""
from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nixal_auditoria_defesa import RegistroAuditoriaDefesaNixOS


def evento(numero: int = 1) -> dict:
    return {
        "id": f"evento_{numero}",
        "observado_em": "2026-10-28T00:00:00+00:00",
        "tipo": "falha_autenticacao",
        "fonte_sinal": "api-auth",
        "origem_ip": "203.0.113.44",
        "estado": "avaliado",
        "severidade": "media",
        "motivos": ["texto livre não deve ser persistido"],
        "headers": {"Authorization": "Bearer CANARY_SECRET_8931"},
        "body": "CANARY_BODY_8931",
        "recomendacoes": [
            {
                "tipo": "bloqueio_temporario_origem",
                "escopo": "203.0.113.44",
                "motivo": "CANARY_REASON_8931",
                "exige_aprovacao_humana": True,
            },
            {"tipo": "acao_nao_allowlisted", "segredo": "CANARY_BAD_8931"},
        ],
        "planos_dry_run": [
            {
                "tipo": "bloqueio_temporario_origem",
                "estado": "aguardando_aprovacao",
                "plano_id": "plano_1",
                "expira_em": "2026-10-28T00:05:00+00:00",
                "exige_aprovacao_humana": True,
                "aprovacao_verificada": False,
                "executor_autorizado": True,
                "efeito_executado": True,
                "token": "CANARY_PLAN_8931",
            }
        ],
        "executor_ativo": True,
        "executor_autorizado": True,
        "efeito_executado": True,
    }


class TestAuditoriaDefesaDuravel(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.caminho = self.root / "private" / "eventos.jsonl"
        self.auditoria = RegistroAuditoriaDefesaNixOS(self.caminho)

    def test_append_persiste_metadados_allowlisted_e_encadeados(self) -> None:
        result = self.auditoria.registrar(evento())
        self.assertTrue(result["sucesso"], result)
        result2 = self.auditoria.registrar(evento(2))
        self.assertTrue(result2["sucesso"], result2)

        registros = self.auditoria.listar(limite=50)
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0]["previous_hash"], "0" * 64)
        self.assertEqual(registros[1]["previous_hash"], registros[0]["entry_hash"])
        self.assertEqual(registros[0]["origem_ip"], "203.0.113.44")
        self.assertFalse(registros[0]["executor_ativo"])
        self.assertFalse(registros[0]["executor_autorizado"])
        self.assertFalse(registros[0]["efeito_executado"])

        bruto = self.caminho.read_bytes()
        for segredo in (
            b"CANARY_SECRET_8931",
            b"CANARY_BODY_8931",
            b"CANARY_REASON_8931",
            b"CANARY_BAD_8931",
            b"CANARY_PLAN_8931",
        ):
            self.assertNotIn(segredo, bruto)
        self.assertEqual(stat.S_IMODE(self.caminho.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.caminho.parent.stat().st_mode), 0o700)

        reconstruida = RegistroAuditoriaDefesaNixOS(self.caminho)
        contexto = reconstruida.contexto()
        self.assertTrue(contexto["integridade_verificada"], contexto)
        self.assertEqual(contexto["quantidade_registros"], 2)

    def test_rejeita_evento_nao_allowlisted_sem_criar_registro(self) -> None:
        invalido = evento()
        invalido["fonte_sinal"] = "cliente"
        resultado = self.auditoria.registrar(invalido)
        self.assertFalse(resultado["sucesso"])
        self.assertFalse(self.caminho.exists())

    def test_corrupcao_detectada_e_arquivo_original_preservado(self) -> None:
        self.assertTrue(self.auditoria.registrar(evento())["sucesso"])
        original = self.caminho.read_bytes()
        linha = json.loads(original.decode("utf-8"))
        linha["origem_ip"] = "198.51.100.72"
        self.caminho.write_text(
            json.dumps(linha, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        corrompido = self.caminho.read_bytes()

        contexto = self.auditoria.contexto()
        self.assertFalse(contexto["integridade_verificada"])
        resultado = self.auditoria.registrar(evento(2))
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(self.caminho.read_bytes(), corrompido)

    def test_symlink_de_arquivo_ou_pasta_e_bloqueado(self) -> None:
        self.caminho.parent.mkdir(mode=0o700)
        destino = self.root / "fora.jsonl"
        sentinel = b"preserve externo\n"
        destino.write_bytes(sentinel)
        self.caminho.symlink_to(destino)
        resultado = self.auditoria.registrar(evento())
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(destino.read_bytes(), sentinel)

    def test_limite_de_registros_recusa_sem_descartar_evidencia(self) -> None:
        limitada = RegistroAuditoriaDefesaNixOS(
            self.caminho, max_bytes=4096, max_registros=2
        )
        self.assertTrue(limitada.registrar(evento(1))["sucesso"])
        self.assertTrue(limitada.registrar(evento(2))["sucesso"])
        original = self.caminho.read_bytes()
        terceiro = limitada.registrar(evento(3))
        self.assertFalse(terceiro["sucesso"])
        self.assertEqual(terceiro["estado"], "limite_registros_atingido")
        self.assertEqual(self.caminho.read_bytes(), original)

    def test_gravacoes_concorrentes_preservam_cadeia(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            resultados = list(pool.map(lambda n: self.auditoria.registrar(evento(n)), range(1, 25)))
        self.assertTrue(all(item["sucesso"] for item in resultados), resultados)
        contexto = self.auditoria.contexto()
        self.assertTrue(contexto["integridade_verificada"], contexto)
        self.assertEqual(contexto["quantidade_registros"], 24)


if __name__ == "__main__":
    unittest.main()
