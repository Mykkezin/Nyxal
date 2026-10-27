#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ollama_fake = types.ModuleType("ollama")
ollama_fake.chat = lambda **_kwargs: {"message": {"content": "unused"}}
sys.modules.setdefault("ollama", ollama_fake)

from nixal_capacidades import GerenciadorCapacidades
from nixal_dialogo_qwen import DialogoQwenNixal
import nixal_tool_use as tools


class ClienteFake:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def chat(self, **kwargs):
        self.chamadas.append(kwargs)
        if not self.respostas:
            return {"message": {"content": "resposta padrão"}}
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def mensagem_tool(nome, argumentos, call_id="call-1"):
    return {"message": {"content": "", "tool_calls": [
        {"id": call_id, "function": {"name": nome, "arguments": argumentos}}
    ]}}


class TestNyxalFunctionCalling(unittest.TestCase):
    def test_dialogo_normal_sem_chamada_de_ferramenta(self):
        cliente = ClienteFake([{"message": {"content": "Olá!"}}])
        dialogo = DialogoQwenNixal(cliente=cliente)
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=None):
            result = dialogo.responder("Oi")
        self.assertTrue(result["sucesso"])
        self.assertEqual(result["resposta"], "Olá!")
        self.assertEqual(result["quantidade_ferramentas"], 0)

    def test_chamada_de_ferramenta_e_resultado_volta_ao_modelo(self):
        cliente = ClienteFake([
            mensagem_tool("obter_hora", {}),
            {"message": {"content": "Consultei a hora com a ferramenta."}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = GerenciadorCapacidades()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            result = dialogo.responder("Que horas são?")
        self.assertTrue(result["sucesso"])
        self.assertEqual(result["quantidade_ferramentas"], 1)
        self.assertEqual(result["ferramentas_executadas"][0]["name"], "obter_hora")
        self.assertEqual(len(cliente.chamadas), 2)
        self.assertTrue(any(item.get("role") == "tool" for item in cliente.chamadas[1]["messages"]))

    def test_ferramenta_desconhecida_nao_executa(self):
        cliente = ClienteFake([
            mensagem_tool("apagar_tudo", {}),
            {"message": {"content": "A ferramenta não está disponível."}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = GerenciadorCapacidades()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            result = dialogo.responder("Faça algo")
        self.assertEqual(result["ferramentas_executadas"][0]["ok"], False)
        self.assertEqual(result["ferramentas_executadas"][0]["resultado"], "Ferramenta não registrada/permitida.")

    def test_catalogo_nao_expoe_privados_ou_mutaveis_por_padrao(self):
        manager = GerenciadorCapacidades()
        dialogo = DialogoQwenNixal(cliente=ClienteFake([]))
        with patch.dict(os.environ, {}, clear=True):
            names = {
                item["function"]["name"]
                for item in dialogo._especificacoes_ferramentas(manager)
            }
        self.assertTrue({
            "obter_hora", "pesquisar_web", "consultar_metar_taf",
            "consultar_notam_aisweb", "consultar_cartas_aisweb",
            "executar_diagnostico",
        } <= names)
        for blocked in ("listar_arquivos", "ler_arquivo", "ler_estado_corpo", "consultar_emails_google",
                        "consultar_agenda_google", "consultar_home_assistant", "salvar_nota",
                        "criar_lembrete", "abrir_aplicativo"):
            self.assertNotIn(blocked, names)

    def test_escrita_sem_pedido_explicito_bloqueada(self):
        cliente = ClienteFake([
            mensagem_tool("salvar_nota", {"titulo": "Teste", "conteudo": "Não salvar"}),
            {"message": {"content": "Ação bloqueada."}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = GerenciadorCapacidades()
        # Ativa a capacidade de notas apenas para testar a política real.
        with tempfile.TemporaryDirectory() as tmp:
            store = tools.NotasLembretesNixOS(Path(tmp) / "notas.json")
            tools.registrar_capacidades_operacionais(manager, incluir_acoes=True, store=store)
            with patch.dict(os.environ, {"NYXAL_ENABLE_MUTABLE_TOOLS": "1"}), patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
                result = dialogo.responder("Responda somente, não salve nada.")
        first = result["ferramentas_executadas"][0]
        self.assertFalse(first["ok"])
        self.assertIn("falta pedido explícito", first["resultado"])
        self.assertFalse(Path(store.arquivo).exists())

    def test_escrita_com_pedido_explicito_e_autorizada(self):
        cliente = ClienteFake([
            mensagem_tool("salvar_nota", {"titulo": "Estudo", "conteudo": "Revisar navegação"}),
            {"message": {"content": "Nota salva."}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = GerenciadorCapacidades()
        with tempfile.TemporaryDirectory() as tmp:
            store = tools.NotasLembretesNixOS(Path(tmp) / "notas.json")
            tools.registrar_capacidades_operacionais(manager, incluir_acoes=True, store=store)
            with patch.dict(os.environ, {"NYXAL_ENABLE_MUTABLE_TOOLS": "1"}), patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
                result = dialogo.responder("Anote que devo revisar navegação.")
            self.assertTrue(result["ferramentas_executadas"][0]["ok"])
            self.assertTrue(Path(store.arquivo).is_file())
            self.assertEqual(json.loads(Path(store.arquivo).read_text())["notas"][0]["titulo"], "Estudo")

    def test_limite_impede_loop_infinito_de_tools(self):
        cliente = ClienteFake([mensagem_tool("obter_hora", {}) for _ in range(10)] + [
            {"message": {"content": "Limite alcançado; resposta final."}}
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = GerenciadorCapacidades()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            result = dialogo.responder("Que horas são?")
        self.assertTrue(result["sucesso"])
        self.assertEqual(len(result["ferramentas_executadas"]), dialogo.MAX_TOOL_CALLS)
        self.assertEqual(len(cliente.chamadas), dialogo.MAX_TOOL_CALLS + 1)
        self.assertTrue(result["resposta"].strip())
        self.assertNotIn("tools", cliente.chamadas[-1])

    def test_capability_schema_enum_e_limites(self):
        manager = GerenciadorCapacidades()
        manager.registrar(
            nome="fake", descricao="Fake", objetivo="Fake", exemplos=["fake"],
            funcao=lambda modo: {"modo": modo},
            argumentos={"modo": {"tipo": "string", "obrigatorio": True, "enum": ["read"], "max_length": 8}},
            dominios=["testes"], evidencias_dominio=["fake"],
        )
        invalid = manager.executar("fake", modo="write")
        self.assertFalse(invalid.sucesso)
        good = manager.executar("fake", modo="read")
        self.assertTrue(good.sucesso)

    def test_pergunta_informativa_nao_autoriza_escrita_ou_abertura(self):
        self.assertFalse(
            DialogoQwenNixal._pedido_explicitamente_autorizou(
                "salvar_nota", "Como faço para salvar nota?"
            )
        )
        self.assertFalse(
            DialogoQwenNixal._pedido_explicitamente_autorizou(
                "abrir_aplicativo", "Como abrir o terminal?"
            )
        )
        self.assertFalse(
            DialogoQwenNixal._pedido_explicitamente_autorizou(
                "abrir_aplicativo", "O que devo fazer para abrir navegador?"
            )
        )
        self.assertTrue(
            DialogoQwenNixal._pedido_explicitamente_autorizou(
                "abrir_aplicativo", "Por favor, abra o navegador."
            )
        )


    def test_limite_nao_faz_chamada_de_modelo_extra(self):
        cliente = ClienteFake([mensagem_tool("obter_hora", {}) for _ in range(10)])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = GerenciadorCapacidades()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            result = dialogo.responder("Que horas são?")
        self.assertTrue(result["sucesso"])
        self.assertEqual(len(result["ferramentas_executadas"]), dialogo.MAX_TOOL_CALLS)
        self.assertEqual(len(cliente.chamadas), dialogo.MAX_TOOL_CALLS + 1)
        self.assertNotIn("tools", cliente.chamadas[-1])
        self.assertIn("limite", result["resposta"].lower())

    def test_limite_aplica_a_chamadas_em_lote(self):
        calls = [
            {"id": f"call-{n}", "function": {"name": "obter_hora", "arguments": {}}}
            for n in range(1, 6)
        ]
        cliente = ClienteFake([
            {"message": {"content": "", "tool_calls": calls}},
            {"message": {"content": "Executei somente as ferramentas permitidas."}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = GerenciadorCapacidades()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            result = dialogo.responder("Que horas são?")

        self.assertTrue(result["sucesso"])
        self.assertEqual(len(result["ferramentas_executadas"]), dialogo.MAX_TOOL_CALLS)
        self.assertEqual(len(cliente.chamadas), 2)
        self.assertNotIn("tools", cliente.chamadas[-1])
        self.assertEqual(
            [x["tool_call_id"] for x in result["ferramentas_executadas"]],
            ["call-1", "call-2", "call-3"],
        )

    def test_pergunta_que_menciona_acao_nao_autoriza(self):
        exemplos = [
            ("salvar_nota", "Como faço para salvar nota?"),
            ("salvar_nota", "Não anote nada."),
            ("criar_lembrete", "Você pode me lembrar de estudar?"),
            ("abrir_aplicativo", "Como abrir o terminal?"),
            ("abrir_aplicativo", "Não abra o navegador."),
        ]
        for nome, texto in exemplos:
            with self.subTest(nome=nome, texto=texto):
                self.assertFalse(DialogoQwenNixal._pedido_explicitamente_autorizou(nome, texto))

    def test_escrita_bloqueada_sem_autorizacao_no_gerenciador(self):
        manager = GerenciadorCapacidades()
        manager.registrar(
            nome="write", descricao="write", objetivo="write", exemplos=["write"],
            funcao=lambda: "escrito", argumentos={}, dominios=["testes"], evidencias_dominio=["write"],
            politica="acao_com_pedido_explicito",
        )
        result = manager.executar("write")
        self.assertFalse(result.sucesso)
        self.assertIn("falta pedido explícito", result.erro)
        allowed = manager.executar("write", autorizacao_explicita=True)
        self.assertTrue(allowed.sucesso)

    def test_servico_home_assistant_somente_leitura_e_config_pendente(self):
        with patch.dict(os.environ, {"NYXAL_HOME_ASSISTANT_URL": "", "NYXAL_HOME_ASSISTANT_TOKEN": ""}):
            result = tools.consultar_home_assistant()
        self.assertEqual(result["estado"], "configuracao_pendente")
        self.assertFalse(result["acoes_fisicas_habilitadas"])

    def test_metar_valida_icao(self):
        result = tools.consultar_metar_taf("SB")
        self.assertEqual(result["estado"], "icao_invalido")

    def test_lembrete_nao_grava_sobre_json_corrompido(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notas.json"
            corrupted = "{not json"
            path.write_text(corrupted)
            store = tools.NotasLembretesNixOS(path)
            with self.assertRaises(RuntimeError):
                store.salvar_nota("Título", "Texto")
            self.assertEqual(path.read_text(), corrupted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
