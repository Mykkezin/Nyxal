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
import nixal_fila_tarefas
from nixal_capacidades import GerenciadorCapacidades
from nixal_fila_tarefas import FilaTarefasNixal
from nixal_executor_ordens import ExecutorOrdensNixal


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
        with_private_key_text = self.fila.adicionar(
            "queue_test_read", {"texto": "PRIVATE_KEY=private-key-in-plain-text"}
        )
        self.assertFalse(with_private_key_text["sucesso"])
        self.assertEqual(with_private_key_text["estado"], "argumentos_invalidos")
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

    def test_idempotency_keys_reject_credentials_on_ingress_and_reload(self):
        incoming = self.fila.adicionar(
            "queue_test_read",
            chave_idempotencia="token=CANARY_IDEMPOTENCY_INPUT",
        )
        self.assertFalse(incoming["sucesso"])
        self.assertEqual(incoming["estado"], "chave_idempotencia_invalida")
        self.assertFalse(self.caminho.exists())

        tarefa = self._registro_legado_valido()
        tarefa["chave_idempotencia"] = "PRIVATE_KEY=CANARY_IDEMPOTENCY_DISK"
        original = json.dumps(
            {"versao": "1.0", "tarefas": [tarefa]},
            separators=(",", ":"),
        ).encode()
        self.caminho.write_bytes(original)
        recarregada = FilaTarefasNixal(self.caminho, self.manager)
        resultado = recarregada.recarregar()
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(self.caminho.read_bytes(), original)

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

    def test_expected_task_id_preserves_fifo_and_does_not_run_an_earlier_task_as_the_answer(self):
        first = self.fila.adicionar("queue_test_read")
        second = self.fila.adicionar("queue_test_read")
        first_id = first["valor"]["id"]
        second_id = second["valor"]["id"]

        waiting = self.fila.executar_proxima(tarefa_id_esperado=second_id)
        self.assertFalse(waiting["sucesso"])
        self.assertEqual(waiting["estado"], "tarefa_aguarda_ordem")
        self.assertFalse(waiting["valor"]["executada"])
        self.assertTrue(waiting["valor"]["ordem_preservada"])
        self.assertEqual(self.chamadas, 0)
        self.assertEqual(self.fila.quantidade_pendentes(), 2)

        done_first = self.fila.executar_proxima(tarefa_id_esperado=first_id)
        self.assertTrue(done_first["sucesso"])
        self.assertEqual(done_first["valor"]["id"], first_id)
        self.assertEqual(done_first["estado"], "concluida")
        self.assertEqual(self.chamadas, 1)

        done_second = self.fila.executar_proxima(tarefa_id_esperado=second_id)
        self.assertTrue(done_second["sucesso"])
        self.assertEqual(done_second["valor"]["id"], second_id)
        self.assertEqual(done_second["estado"], "concluida")
        self.assertEqual(self.chamadas, 2)

    def test_executor_ordens_does_not_mislabel_earlier_pending_task_as_new_order(self):
        self.fila.adicionar("queue_test_read")

        class AgenteFalso:
            def __init__(self, capacidades):
                self.capacidades = capacidades

            @staticmethod
            def selecionar_capacidade(ordem):
                return {
                    "sucesso": True,
                    "capacidade": "queue_test_read",
                    "argumentos": {},
                    "motivo": "capacidade de leitura controlada no teste",
                }

        executor = ExecutorOrdensNixal(agente=AgenteFalso(self.manager), fila=self.fila)
        resposta = executor.atender("Consulte a informação de teste.")

        self.assertTrue(resposta["sucesso"])
        self.assertEqual(resposta["estado"], "tarefa_enfileirada_aguardando_ordem")
        self.assertFalse(resposta["valor"]["executada"])
        self.assertEqual(resposta["valor"]["execucao"]["estado"], "tarefa_aguarda_ordem")
        self.assertEqual(self.chamadas, 0)
        self.assertEqual(self.fila.quantidade_pendentes(), 2)

    def test_invalid_expected_task_id_is_rejected_without_execution(self):
        resultado = self.fila.executar_proxima(tarefa_id_esperado=" " * 3)
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["estado"], "tarefa_id_invalido")
        self.assertEqual(self.chamadas, 0)

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
            "diagnostic": "PRIVATE_KEY=CANARY_QUEUE_PRIVATE_KEY_TEXT",
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
        self.assertNotIn("CANARY_QUEUE_PRIVATE_KEY_TEXT", encoded)
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


    @staticmethod
    def _registro_legado_valido(capacidade: str = "queue_test_read") -> dict:
        return {
            "id": "legacy-task-id",
            "capacidade": capacidade,
            "argumentos": {},
            "estado": "concluida",
            "criado_em": time.time(),
            "resultado": {"sucesso": True},
            "erro": None,
        }

    def test_default_queue_migrates_legacy_snapshot_without_modifying_it(self):
        legado = self.root / "checkout" / "fila_tarefas_nixal.json"
        legado.parent.mkdir()
        destino = self.root / "user-data" / "nyxal" / "fila_tarefas_nixal.json"
        dados = {"versao": "1.0", "tarefas": [self._registro_legado_valido()]}
        original = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        legado.write_bytes(original)

        with (
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_PADRAO", destino),
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_LEGADO", legado),
        ):
            fila = FilaTarefasNixal(capacidades=self.manager)
            self.assertEqual(fila.quantidade(), 1)

        self.assertTrue(destino.is_file())
        self.assertEqual(destino.stat().st_mode & 0o777, 0o600)
        self.assertEqual(legado.read_bytes(), original)
        self.assertEqual(json.loads(destino.read_text(encoding="utf-8"))["tarefas"][0]["id"], "legacy-task-id")

    def test_existing_user_queue_takes_precedence_over_legacy_snapshot(self):
        legado = self.root / "checkout" / "fila_tarefas_nixal.json"
        legado.parent.mkdir()
        destino = self.root / "user-data" / "nyxal" / "fila_tarefas_nixal.json"
        destino.parent.mkdir(parents=True, mode=0o700)
        dados_legado = {"versao": "1.0", "tarefas": [self._registro_legado_valido()]}
        dados_usuario = {"versao": "1.0", "tarefas": [self._registro_legado_valido("queue_test_slow_read")]}
        bytes_legado = json.dumps(dados_legado).encode("utf-8")
        bytes_usuario = json.dumps(dados_usuario).encode("utf-8")
        legado.write_bytes(bytes_legado)
        destino.write_bytes(bytes_usuario)
        with (
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_PADRAO", destino),
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_LEGADO", legado),
        ):
            fila = FilaTarefasNixal(capacidades=self.manager)
            self.assertEqual(fila.quantidade(), 1)
            self.assertEqual(fila.listar()[0]["capacidade"], "queue_test_slow_read")
        self.assertEqual(destino.read_bytes(), bytes_usuario)
        self.assertEqual(legado.read_bytes(), bytes_legado)

    def test_corrupt_legacy_snapshot_fails_closed_without_creating_blank_queue(self):
        legado = self.root / "checkout" / "fila_tarefas_nixal.json"
        legado.parent.mkdir()
        destino = self.root / "user-data" / "nyxal" / "fila_tarefas_nixal.json"
        original = b'{"versao":"1.0","tarefas":[broken'
        legado.write_bytes(original)
        with (
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_PADRAO", destino),
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_LEGADO", legado),
        ):
            fila = FilaTarefasNixal(capacidades=self.manager)
            resultado = fila.adicionar("queue_test_read")
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["estado"], "fila_indisponivel_preservada")
        self.assertFalse(destino.exists())
        self.assertEqual(legado.read_bytes(), original)


    def test_legacy_results_and_errors_are_redacted_before_listing(self):
        tarefa = {
            "id": "legacy-secret-task",
            "capacidade": "queue_test_read",
            "argumentos": {},
            "estado": "concluida",
            "criado_em": time.time(),
            "resultado": {
                "sucesso": True,
                "api_key": "CANARY_QUEUE_RESULT_KEY",
                "mensagem": "Authorization: Bearer CANARY_QUEUE_RESULT_TOKEN",
            },
            "erro": "falha antiga token=CANARY_QUEUE_ERROR",
        }
        self.caminho.write_text(
            json.dumps({"versao": "1.0", "tarefas": [tarefa]}),
            encoding="utf-8",
        )
        self.caminho.chmod(0o644)

        fila = FilaTarefasNixal(self.caminho, self.manager)
        dados_listados = fila.listar()
        serializado = json.dumps(dados_listados, ensure_ascii=False)
        bytes_persistidos = self.caminho.read_bytes()

        for segredo in (
            "CANARY_QUEUE_RESULT_KEY",
            "CANARY_QUEUE_RESULT_TOKEN",
            "CANARY_QUEUE_ERROR",
        ):
            self.assertNotIn(segredo, serializado)
            self.assertNotIn(segredo.encode(), bytes_persistidos)
        self.assertEqual(self.caminho.stat().st_mode & 0o777, 0o600)
        self.assertIn("[REDACTED]", serializado)

    def test_unknown_task_fields_fail_closed_and_original_is_preserved(self):
        tarefa = {
            "id": "legacy-extra-field",
            "capacidade": "queue_test_read",
            "argumentos": {},
            "estado": "concluida",
            "criado_em": time.time(),
            "resultado": None,
            "erro": None,
            "debug_payload": "CANARY_UNKNOWN_FIELD_77",
        }
        original = json.dumps(
            {"versao": "1.0", "tarefas": [tarefa]},
            separators=(",", ":"),
        ).encode()
        self.caminho.write_bytes(original)

        fila = FilaTarefasNixal(self.caminho, self.manager)
        resultado = fila.recarregar()
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["estado"], "fila_corrompida_preservada")
        self.assertEqual(self.caminho.read_bytes(), original)
        self.assertEqual(fila.listar(), [])

    def test_duplicate_json_keys_fail_closed_and_preserve_original(self):
        original = (
            b'{"versao":"1.0","tarefas":[{"id":"duplicate","capacidade":"queue_test_read",'
            b'"argumentos":{},"estado":"concluida","estado":"pendente","criado_em":1,'
            b'"resultado":null,"erro":null}]}'
        )
        self.caminho.write_bytes(original)
        fila = FilaTarefasNixal(self.caminho, self.manager)
        resultado = fila.recarregar()
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(self.caminho.read_bytes(), original)

    def test_extreme_integer_timestamp_fails_closed_without_crashing(self):
        tarefa = {
            "id": "extreme-int-time",
            "capacidade": "queue_test_read",
            "argumentos": {},
            "estado": "concluida",
            "criado_em": 10**400,
            "resultado": None,
            "erro": None,
        }
        original = json.dumps(
            {"versao": "1.0", "tarefas": [tarefa]},
            separators=(",", ":"),
        ).encode()
        self.caminho.write_bytes(original)

        fila = FilaTarefasNixal(self.caminho, self.manager)
        resultado = fila.recarregar()
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(self.caminho.read_bytes(), original)

    def test_world_writable_queue_directory_is_rejected(self):
        pasta = self.root / "unsafe-dir"
        pasta.mkdir(mode=0o700)
        pasta.chmod(0o777)
        caminho = pasta / "fila.json"

        with self.assertRaises(PermissionError):
            FilaTarefasNixal(caminho, self.manager)
        self.assertFalse(caminho.exists())

    def test_group_readable_queue_directory_is_made_private(self):
        pasta = self.root / "less-private-dir"
        pasta.mkdir(mode=0o700)
        pasta.chmod(0o755)
        caminho = pasta / "fila.json"

        fila = FilaTarefasNixal(caminho, self.manager)
        resultado = fila.recarregar()

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(os.stat(pasta).st_mode & 0o777, 0o700)
        self.assertFalse(caminho.exists())

    def test_legacy_migration_redacts_old_result_and_error(self):
        legado = self.root / "checkout" / "fila_tarefas_nixal.json"
        legado.parent.mkdir()
        destino = self.root / "user-data" / "nyxal" / "fila_tarefas_nixal.json"
        tarefa = self._registro_legado_valido()
        tarefa["resultado"] = {
            "sucesso": True,
            "access_token": "CANARY_MIGRATION_TOKEN_991",
            "mensagem": "Authorization: Bearer CANARY_MIGRATION_BEARER_991",
        }
        tarefa["erro"] = "token=CANARY_MIGRATION_ERROR_991"
        original = json.dumps(
            {"versao": "1.0", "tarefas": [tarefa]},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        legado.write_bytes(original)

        with (
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_PADRAO", destino),
            patch.object(nixal_fila_tarefas, "ARQUIVO_FILA_LEGADO", legado),
        ):
            fila = FilaTarefasNixal(capacidades=self.manager)
            itens = fila.listar()
            serializado = json.dumps(itens, ensure_ascii=False)
            bytes_destino = destino.read_bytes()
        for segredo in (
            "CANARY_MIGRATION_TOKEN_991",
            "CANARY_MIGRATION_BEARER_991",
            "CANARY_MIGRATION_ERROR_991",
        ):
            self.assertNotIn(segredo, serializado)
            self.assertNotIn(segredo.encode(), bytes_destino)
        self.assertEqual(legado.read_bytes(), original)
        self.assertEqual(destino.stat().st_mode & 0o777, 0o600)

if __name__ == "__main__":
    unittest.main()
