#!/usr/bin/env python3
"""Testes de escrita governada no workspace, com plano, hash e confirmação em outro turno."""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.modules.setdefault("ollama", types.SimpleNamespace())

import nixal_capacidades
import nixal_tool_use
from nixal_capacidades import GerenciadorCapacidades
from nixal_dialogo_qwen import DialogoQwenNixal
from nixal_tool_use import (
    NotasLembretesNixOS,
    aplicar_edicao_workspace,
    preparar_edicao_workspace,
    registrar_capacidades_operacionais,
)


class ClienteFake:
    def chat(self, **kwargs):
        return {"message": {"content": "Resposta textual de teste."}}


def chamada_tool(nome: str, argumentos: dict) -> dict:
    return {
        "id": "workspace-test-call",
        "type": "function",
        "function": {"name": nome, "arguments": argumentos},
    }


class TesteEdicaoWorkspaceGovernada(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nyxal-workspace-edits-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.workspace = base / "workspace"
        self.workspace.mkdir()
        self.data = base / "user-data"
        (self.workspace / "src").mkdir()
        self.target = self.workspace / "src" / "app.py"
        self.target.write_text("valor = 1\n", encoding="utf-8")

        self.env = patch.dict(os.environ, {
            "NYXAL_WORKSPACE_WRITE_ROOT": str(self.workspace),
            "NYXAL_USER_DATA_DIR": str(self.data),
            "NYXAL_ENABLE_MUTABLE_TOOLS": "1",
            "NYXAL_ENABLE_WORKSPACE_WRITE": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

        self.user_data_patch = patch.object(nixal_tool_use, "DEFAULT_USER_DATA_DIR", self.data)
        self.user_data_patch.start()
        self.addCleanup(self.user_data_patch.stop)

        self.cap_patch = patch.object(
            nixal_capacidades, "ARQUIVO_CAPACIDADES", base / "capacidades.json"
        )
        self.log_patch = patch.object(
            nixal_capacidades, "ARQUIVO_LOG", base / "auditoria.jsonl"
        )
        self.cap_patch.start()
        self.log_patch.start()
        self.addCleanup(self.cap_patch.stop)
        self.addCleanup(self.log_patch.stop)

        with nixal_tool_use._WORKSPACE_PLAN_LOCK:
            nixal_tool_use._WORKSPACE_PLANS.clear()

        self.manager = GerenciadorCapacidades()
        registrar_capacidades_operacionais(
            self.manager,
            incluir_acoes=True,
            incluir_edicao_workspace=True,
            store=NotasLembretesNixOS(base / "notas.json"),
        )
        self.dialogo = DialogoQwenNixal(cliente=ClienteFake())

    def tearDown(self) -> None:
        with nixal_tool_use._WORKSPACE_PLAN_LOCK:
            nixal_tool_use._WORKSPACE_PLANS.clear()

    def test_workspace_write_is_opt_in_and_requires_mutable_tools(self):
        manager = GerenciadorCapacidades()
        registrar_capacidades_operacionais(manager)
        self.assertNotIn("preparar_edicao_workspace", manager.capacidades)
        self.assertNotIn("aplicar_edicao_workspace", manager.capacidades)

        with self.assertRaises(ValueError):
            registrar_capacidades_operacionais(
                manager, incluir_acoes=False, incluir_edicao_workspace=True
            )

    def test_handlers_stay_disabled_without_both_opt_ins(self):
        with patch.dict(os.environ, {
            "NYXAL_ENABLE_MUTABLE_TOOLS": "",
            "NYXAL_ENABLE_WORKSPACE_WRITE": "",
        }):
            prepared = preparar_edicao_workspace("src/app.py", "valor = 7\n")
        self.assertFalse(prepared["sucesso"])
        self.assertEqual(prepared["estado"], "workspace_edicao_desativada")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 1\n")

        plan = preparar_edicao_workspace("src/app.py", "valor = 9\n")
        with patch.dict(os.environ, {
            "NYXAL_ENABLE_MUTABLE_TOOLS": "",
            "NYXAL_ENABLE_WORKSPACE_WRITE": "",
        }):
            applied = aplicar_edicao_workspace(plan["plano_id"], plan["confirmacao_exata"])
        self.assertFalse(applied["sucesso"])
        self.assertEqual(applied["estado"], "workspace_edicao_desativada")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 1\n")

    def test_prepare_returns_diff_without_writing_target(self):
        result = preparar_edicao_workspace("src/app.py", "valor = 2\n")
        self.assertTrue(result["sucesso"])
        self.assertEqual(result["estado"], "plano_preparado")
        self.assertFalse(result["aplicado"])
        self.assertIn("valor = 2", result["diff"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 1\n")
        self.assertEqual(
            result["confirmacao_exata"],
            f"CONFIRMO APLICACAO {result['plano_id']}",
        )

    def test_apply_creates_private_backup_and_replaces_atomically(self):
        original = self.target.read_bytes()
        result = preparar_edicao_workspace("src/app.py", "valor = 42\n")
        applied = aplicar_edicao_workspace(
            result["plano_id"], result["confirmacao_exata"]
        )
        self.assertTrue(applied["sucesso"])
        self.assertTrue(applied["aplicado"])
        self.assertEqual(applied["estado"], "arquivo_atualizado")
        self.assertEqual(self.target.read_bytes(), b"valor = 42\n")
        backup = self.data / "workspace-backups" / f"{result['plano_id']}.bak"
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertFalse(aplicar_edicao_workspace(
            result["plano_id"], result["confirmacao_exata"]
        )["sucesso"])

    def test_apply_does_not_overwrite_preexisting_backup(self):
        result = preparar_edicao_workspace("src/app.py", "valor = 19\n")
        self.assertTrue(result["sucesso"])

        backup_dir = self.data / "workspace-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"{result['plano_id']}.bak"
        sentinel = b"preserve existing backup"
        backup.write_bytes(sentinel)

        applied = aplicar_edicao_workspace(
            result["plano_id"], result["confirmacao_exata"]
        )
        self.assertFalse(applied["sucesso"])
        self.assertEqual(applied["estado"], "backup_destino_ja_existe")
        self.assertFalse(applied["aplicado"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 1\n")
        self.assertEqual(backup.read_bytes(), sentinel)
        self.assertEqual(
            list(backup_dir.glob(f".{result['plano_id']}-*")),
            [],
            "Temporary backup files must be cleaned up on refusal.",
        )

    def test_stale_plan_does_not_overwrite_concurrent_change(self):
        result = preparar_edicao_workspace("src/app.py", "valor = 3\n")
        self.target.write_text("alteração externa\n", encoding="utf-8")
        applied = aplicar_edicao_workspace(result["plano_id"], result["confirmacao_exata"])
        self.assertFalse(applied["sucesso"])
        self.assertEqual(applied["estado"], "arquivo_alterado_desde_o_plano")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "alteração externa\n")

    def test_apply_requires_exact_current_turn_confirmation(self):
        result = preparar_edicao_workspace("src/app.py", "valor = 8\n")
        plan_id = result["plano_id"]
        token = result["confirmacao_exata"]
        tool_call = chamada_tool("aplicar_edicao_workspace", {
            "plano_id": plan_id, "confirmacao_exata": token,
        })
        refused = self.dialogo._executar_chamada_ferramenta(
            self.manager, tool_call, "Pode aplicar a edição agora."
        )
        self.assertFalse(refused["ok"])
        self.assertIn("pedido explícito", refused["resultado"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 1\n")

        id_errado = ("0" if not plan_id.startswith("0") else "1") + plan_id[1:]
        chamada_com_token_errado = chamada_tool("aplicar_edicao_workspace", {
            "plano_id": plan_id,
            "confirmacao_exata": f"CONFIRMO APLICACAO {id_errado}",
        })
        token_argumento_recusado = self.dialogo._executar_chamada_ferramenta(
            self.manager, chamada_com_token_errado, token
        )
        self.assertFalse(token_argumento_recusado["ok"])
        self.assertIn("pedido explícito", token_argumento_recusado["resultado"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 1\n")

        accepted = self.dialogo._executar_chamada_ferramenta(
            self.manager, tool_call, token
        )
        self.assertTrue(accepted["ok"], accepted)
        self.assertIn('"aplicado": true', accepted["resultado"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 8\n")

    def test_tool_is_not_advertised_without_both_opt_ins(self):
        with patch.dict(os.environ, {
            "NYXAL_ENABLE_MUTABLE_TOOLS": "1",
            "NYXAL_ENABLE_WORKSPACE_WRITE": "",
        }):
            names = {
                item["function"]["name"]
                for item in self.dialogo._especificacoes_ferramentas(self.manager)
            }
        self.assertNotIn("preparar_edicao_workspace", names)
        self.assertNotIn("aplicar_edicao_workspace", names)

        with patch.dict(os.environ, {
            "NYXAL_ENABLE_MUTABLE_TOOLS": "",
            "NYXAL_ENABLE_WORKSPACE_WRITE": "1",
        }):
            names = {
                item["function"]["name"]
                for item in self.dialogo._especificacoes_ferramentas(self.manager)
            }
        self.assertNotIn("preparar_edicao_workspace", names)
        self.assertNotIn("aplicar_edicao_workspace", names)

    def test_traversal_sensitive_and_symlink_targets_are_blocked(self):
        outside = Path(self.temp.name) / "fora.py"
        outside.write_text("nao tocar\n", encoding="utf-8")
        resultado = preparar_edicao_workspace("../fora.py", "mude\n")
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(outside.read_text(encoding="utf-8"), "nao tocar\n")

        (self.workspace / ".env").write_text("SECRET=valor\n", encoding="utf-8")
        blocked = preparar_edicao_workspace(".env", "SECRET=novo\n")
        self.assertFalse(blocked["sucesso"])

        for nome_sensivel in ("credentials.yaml", "secrets.json", "api_keys.json", "auth.json"):
            arquivo_sensivel = self.workspace / nome_sensivel
            arquivo_sensivel.write_text("private-value\n", encoding="utf-8")
            proposta_sensivel = preparar_edicao_workspace(nome_sensivel, "changed-value\n")
            self.assertFalse(proposta_sensivel["sucesso"], nome_sensivel)
            self.assertEqual(arquivo_sensivel.read_text(encoding="utf-8"), "private-value\n")

        nomes_operacionais = (
            "estado_corpo_nixal.json",
            "estado_nixal.json",
            "fila_tarefas_nixal.json",
            "log_capacidades_nixal.json",
            "log_nyxal_runtime.json",
            "memoria_investigacao_nixal.json",
            "memoria_conhecimento_nixal.json",
        )
        for nome in nomes_operacionais:
            operacional = self.workspace / nome
            conteudo_original = '{"estado":"preservar"}'
            operacional.write_text(conteudo_original, encoding="utf-8")
            protected = preparar_edicao_workspace(nome, "{}")
            self.assertFalse(protected["sucesso"], nome)
            self.assertEqual(operacional.read_text(encoding="utf-8"), conteudo_original, nome)

        for pasta_sensivel in (".env.d", "backup_estado_2026-10-03", "backups", "voices", "memoria"):
            diretorio = self.workspace / pasta_sensivel
            diretorio.mkdir(exist_ok=True)
            alvo_sensivel = diretorio / "arquivo.py"
            alvo_sensivel.write_text("nao tocar\n", encoding="utf-8")
            bloqueado = preparar_edicao_workspace(
                f"{pasta_sensivel}/arquivo.py", "alterado\n"
            )
            self.assertFalse(bloqueado["sucesso"], pasta_sensivel)
            self.assertEqual(alvo_sensivel.read_text(encoding="utf-8"), "nao tocar\n")

        link = self.workspace / "src" / "alias.py"
        link.symlink_to(outside)
        linked = preparar_edicao_workspace("src/alias.py", "sobrescrever\n")
        self.assertFalse(linked["sucesso"])
        self.assertEqual(outside.read_text(encoding="utf-8"), "nao tocar\n")

    def test_binary_oversized_and_noop_proposals_fail_safely(self):
        binary = preparar_edicao_workspace("src/app.py", "valor = 1\n\x00")
        self.assertFalse(binary["sucesso"])
        oversized = preparar_edicao_workspace(
            "src/app.py", "x" * (nixal_tool_use.MAX_WORKSPACE_EDIT_BYTES + 1)
        )
        self.assertFalse(oversized["sucesso"])
        noop = preparar_edicao_workspace("src/app.py", "valor = 1\n")
        self.assertTrue(noop["sucesso"])
        self.assertEqual(noop["estado"], "sem_alteracoes")
        self.assertNotIn("plano_id", noop)

    def test_sensitive_old_values_are_redacted_from_diff_preview(self):
        casos = (
            (
                "API_TOKEN=private-sample-value\n",
                "API_TOKEN=replacement-value\n",
                "private-sample-value",
            ),
            (
                '{"api_key": "private-json-secret", "valor": 1}\n',
                '{"api_key": "replacement-value", "valor": 2}\n',
                "private-json-secret",
            ),
            (
                "authorization: 'Bearer private-yaml-secret'\n",
                "authorization: 'Bearer replacement-value'\n",
                "private-yaml-secret",
            ),
        )
        for antigo, novo, segredo in casos:
            self.target.write_text(antigo, encoding="utf-8")
            result = preparar_edicao_workspace("src/app.py", novo)
            self.assertTrue(result["sucesso"], result)
            self.assertNotIn(segredo, result["diff"])
            self.assertIn("[REDACTED]", result["diff"])

    def test_apply_refuses_symlinked_backup_directory(self):
        result = preparar_edicao_workspace("src/app.py", "valor = 77\n")
        self.assertTrue(result["sucesso"])
        self.data.mkdir(parents=True, exist_ok=True)
        backup_dir = self.data / "workspace-backups"
        outside = Path(self.temp.name) / "outside-backups"
        outside.mkdir()
        backup_dir.symlink_to(outside, target_is_directory=True)

        applied = aplicar_edicao_workspace(result["plano_id"], result["confirmacao_exata"])
        self.assertFalse(applied["sucesso"])
        self.assertEqual(applied["estado"], "diretorio_backup_com_link_simbolico")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "valor = 1\n")
        self.assertEqual(list(outside.iterdir()), [])


    def test_workspace_authorization_accepts_explicit_correction_not_review_questions(self):
        self.assertTrue(
            self.dialogo._pedido_explicitamente_autorizou(
                "preparar_edicao_workspace", "corrija src/app.py"
            )
        )
        self.assertTrue(
            self.dialogo._pedido_explicitamente_autorizou(
                "preparar_edicao_workspace", "corrija o arquivo src/app.py"
            )
        )
        for pedido in ("como corrijo src/app.py", "corrija src/app.py?", "revise src/app.py"):
            with self.subTest(pedido=pedido):
                self.assertFalse(
                    self.dialogo._pedido_explicitamente_autorizou(
                        "preparar_edicao_workspace", pedido
                    )
                )


if __name__ == "__main__":
    unittest.main()
