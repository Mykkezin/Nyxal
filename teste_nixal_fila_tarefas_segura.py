#!/usr/bin/env python3
"""Regressões de segurança, checkpoint e recuperação da fila de tarefas."""

from __future__ import annotations

import json
import os
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import nixal_capacidades
from nixal_capacidades import GerenciadorCapacidades
from nixal_fila_tarefas import FilaTarefasNixal


class TesteFilaTarefasNixalSegura(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory(prefix="nyxal-task-queue-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.caminho = self.root / "fila.json"
        self.patch_catalogo = patch.object(
            nixal_capacidades, "ARQUIVO_CAPACIDADES", self.root / "capacidades.json"
        )
        self.patch_log = patch.object(
            nixal_capacidades, "ARQUIVO_LOG", self.root / "capacidades.log"
        )
        self.patch_catalogo.start()
        self.patch_log.start()
        self.addCleanup(self.patch_catalogo.stop)
        self.addCleanup(self.patch_log.stop)

        self.chamadas = 0
        self.resultado_controlado: dict = {"status": "ok"}

        def leitura() -> dict:
            self.chamadas += 1
            return dict(self.resultado_controlado)

        def leitura_lenta() -> dict:
            self.chamadas += 1
            self.entrada.set()
            if not self.liberar.wait(timeout=4):
                raise TimeoutError("teste_timeout")
            return {"status": "feito"}

        def mutavel() -> str:
            self.chamadas += 1
            return "não deveria executar"

        self.entrada = threading.Event()
        self.liberar = threading.Event()
        self.manager = GerenciadorCapacidades()
        self.manager.registrar(
            nome="queue_test_read",
            descricao="leitura controlada de teste",
            objetivo="validar fila em testes",
            exemplos=["teste"],
            funcao=leitura,
            argumentos={},
            dominios=["teste"],
            evidencias_dominio=["fila"],
            politica="somente_leitura",
        )
        self.manager.registrar(
            nome="queue_test_slow_read",
            descricao="leitura lenta de teste",
            objetivo="validar exclusão mútua",
            exemplos=["teste"],
            funcao=leitura_lenta,
            argumentos={},
            dominios=["teste"],
            evidencias_dominio=["fila"],
            politica="somente_leitura",
        )
        self.manager.registrar(
            nome="queue_test_mutable",
            descricao="ação mutável de teste",
            objetivo="confirmar bloqueio da fila",
            exemplos=["teste"],
            funcao=mutavel,
            argumentos={},
            dominios=["teste"],
            evidencias_dominio=["fila"],
            politica="acao_com_pedido_explicito",
        )
        self.fila = FilaTarefasNixal(self.caminho, self.manager)

    def test_only_registered_read_only_capabilities_can_be_enqueued(self):
        self.assertTrue(self.fila.adicionar("queue_test_read")["sucesso"])
        missing = self.fila.adicionar("capacidade_inexistente")
        self.assertFalse(missing["sucesso"])
        self.assertEqual(missing["estado"], "capacidade_nao_enfileiravel")
        mutable = self.fila.adicionar("queue_test_mutable")
        self.assertFalse(mutable["sucesso"])
        self.assertIn("mutavel", mutable["motivo"])

    def test_arguments_are_validated_bounded_and_secret_fields_rejected(self):
        with_secret = self.fila.adicionar("queue_test_read", {"api_key": "sample-secret"})
        self.assertFalse(with_secret["sucesso"])
        self.assertEqual(with_secret["estado"], "argumentos_invalidos")
        with_private_key = self.fila.adicionar(
            "queue_test_read", {"ssh_private_key": "private-key-sample"}
        )
        self.assertFalse(with_private_key["sucesso"])
        self.assertEqual(with_private_key["estado"], "argumentos_invalidos")
        too_large = self.fila.adicionar("queue_test_read", {"texto": "x" * 17000})
        self.assertFalse(too_large["sucesso"])
        self.assertEqual(too_large["estado"], "argumentos_excedem_limite")
        bad_float = self.fila.adicionar("queue_test_read", {"valor": float("nan")})
        self.assertFalse(bad_float["sucesso"])

    def test_duplicate_idempotency_key_does_not_create_a_second_task(self):
        first = self.fila.adicionar("queue_test_read", chave_idempotencia="pedido-123")
        second = self.fila.adicionar("queue_test_read", chave_idempotencia="pedido-123")
        self.assertTrue(first["sucesso"])
        self.assertTrue(second["sucesso"])
        self.assertEqual(second["estado"], "ja_existente")
        self.assertEqual(first["valor"]["id"], second["valor"]["id"])
        self.assertEqual(self.fila.quantidade(), 1)

    def test_task_is_persisted_then_claimed_and_completed_once(self):
        added = self.fila.adicionar("queue_test_read")
        self.assertTrue(added["sucesso"])
        restarted = FilaTarefasNixal(self.caminho, self.manager)
        result = restarted.executar_proxima()
        self.assertTrue(result["sucesso"])
        self.assertEqual(result["estado"], "concluida")
        self.assertEqual(self.chamadas, 1)
        self.assertEqual(FilaTarefasNixal(self.caminho, self.manager).quantidade_pendentes(), 0)
        self.assertEqual(restarted.executar_proxima()["estado"], "fila_vazia")
        self.assertEqual(self.chamadas, 1)

    def test_concurrent_workers_do_not_claim_the_same_task(self):
        self.fila.adicionar("queue_test_slow_read")
        outra = FilaTarefasNixal(self.caminho, self.manager)
        resultados: list[dict] = []
        worker = threading.Thread(target=lambda: resultados.append(self.fila.executar_proxima()))
        worker.start()
        self.assertTrue(self.entrada.wait(timeout=3), "a primeira execução não começou")
        second = outra.executar_proxima()
        self.assertFalse(second["sucesso"])
        self.assertEqual(second["estado"], "tarefa_em_execucao")
        self.liberar.set()
        worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(resultados), 1)
        self.assertTrue(resultados[0]["sucesso"])
        self.assertEqual(self.chamadas, 1)

    def test_crashed_execution_becomes_indeterminate_and_is_not_replayed(self):
        tarefa = {
            "id": "a" * 64,
            "capacidade": "queue_test_read",
            "argumentos": {},
            "estado": "executando",
            "criado_em": time.time() - 60,
            "resultado": None,
            "erro": None,
            "execucao_dono": {
                "host": "host-que-nao-existe",
                "pid": 99999999,
                "iniciado_em": time.time() - 60,
                "execucao_id": "exec-crashed",
            },
        }
        self.caminho.write_text(
            json.dumps({"versao": "1.0", "tarefas": [tarefa]}),
            encoding="utf-8",
        )
        recarregada = FilaTarefasNixal(self.caminho, self.manager)
        registros = recarregada.listar()
        self.assertEqual(registros[0]["estado"], "resultado_indeterminado")
        self.assertFalse(registros[0]["resultado"]["repeticao_automatica"])
        self.assertEqual(recarregada.executar_proxima()["estado"], "fila_vazia")
        self.assertEqual(self.chamadas, 0)
        salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertEqual(salvo["tarefas"][0]["estado"], "resultado_indeterminado")

    def test_corrupt_queue_is_preserved_and_blocks_writes(self):
        original = b'{"versao":"1.0","tarefas":[broken'
        self.caminho.write_bytes(original)
        recarregada = FilaTarefasNixal(self.caminho, self.manager)
        self.assertFalse(recarregada.recarregar()["sucesso"])
        denied = recarregada.adicionar("queue_test_read")
        self.assertFalse(denied["sucesso"])
        self.assertEqual(denied["estado"], "fila_indisponivel_preservada")
        self.assertEqual(self.caminho.read_bytes(), original)

    def test_symlinked_queue_file_is_never_read_or_replaced(self):
        outside = self.root / "outside.json"
        original = json.dumps({"do_not_touch": True}).encode()
        outside.write_bytes(original)
        link = self.root / "linked-queue.json"
        link.symlink_to(outside)
        recarregada = FilaTarefasNixal(link, self.manager)
        result = recarregada.adicionar("queue_test_read")
        self.assertFalse(result["sucesso"])
        self.assertTrue(link.is_symlink())
        self.assertEqual(outside.read_bytes(), original)

    def test_result_redacts_secrets_and_bounds_large_output(self):
        self.resultado_controlado = {
            "api_key": "secret-value",
            "ssh_private_key": "private-key-result",
            "message": "Authorization: Bearer private-token",
            "other": ["z" * 9000 for _ in range(10)],
        }
        self.fila.adicionar("queue_test_read")
        result = self.fila.executar_proxima()
        self.assertTrue(result["sucesso"])
        stored = result["valor"]["resultado"]["resultado"]
        encoded = json.dumps(stored, ensure_ascii=False)
        self.assertNotIn("secret-value", encoded)
        self.assertNotIn("private-key-result", encoded)
        self.assertNotIn("private-token", encoded)
        self.assertTrue(stored.get("resultado_truncado"))

    def test_failed_capability_is_terminal_not_auto_retried(self):
        self.manager.registrar(
            nome="queue_test_failure",
            descricao="falha controlada",
            objetivo="validar que falhas não são repetidas",
            exemplos=["teste"],
            funcao=lambda: (_ for _ in ()).throw(RuntimeError("erro de teste")),
            argumentos={},
            dominios=["teste"],
            evidencias_dominio=["fila"],
            politica="somente_leitura",
        )
        self.fila.adicionar("queue_test_failure")
        first = self.fila.executar_proxima()
        self.assertFalse(first["sucesso"])
        self.assertEqual(first["estado"], "falhou")
        second = self.fila.executar_proxima()
        self.assertEqual(second["estado"], "fila_vazia")

    def test_repeated_instances_do_not_lose_enqueued_tasks(self):
        first = FilaTarefasNixal(self.caminho, self.manager)
        second = FilaTarefasNixal(self.caminho, self.manager)
        self.assertTrue(first.adicionar("queue_test_read")["sucesso"])
        self.assertTrue(second.adicionar("queue_test_read")["sucesso"])
        third = FilaTarefasNixal(self.caminho, self.manager)
        self.assertEqual(third.quantidade(), 2)

    def test_unknown_or_corrupt_queue_state_is_not_silently_reset(self):
        original = json.dumps({"versao": "999.0", "tarefas": []}).encode()
        self.caminho.write_bytes(original)
        fila = FilaTarefasNixal(self.caminho, self.manager)
        self.assertEqual(fila.recarregar()["estado"], "fila_corrompida_preservada")
        self.assertEqual(self.caminho.read_bytes(), original)
        self.assertFalse(fila.adicionar("queue_test_read")["sucesso"])


if __name__ == "__main__":
    unittest.main()
