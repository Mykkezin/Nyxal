#!/usr/bin/env python3
"""Regressões de function calling limitado para o diálogo principal da Nyxal."""
from __future__ import annotations

import json
import os
import sys
import types
import unittest
from unittest.mock import patch

# Mantém os testes importáveis em ambientes mínimos sem substituir um Ollama real
# que já tenha sido carregado por outra suíte.
ollama_fake = types.ModuleType("ollama")
ollama_fake.chat = lambda **_kwargs: {"message": {"content": "unused"}}
sys.modules.setdefault("ollama", ollama_fake)

from nixal_capacidades import GerenciadorCapacidades
from nixal_dialogo_qwen import DialogoQwenNixal
from nixal_tool_use import registrar_capacidades_operacionais


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
    return {
        "message": {
            "content": "",
            "tool_calls": [{
                "id": call_id,
                "function": {"name": nome, "arguments": argumentos},
            }],
        }
    }


class TestNyxalFunctionCalling(unittest.TestCase):
    def manager(self):
        manager = GerenciadorCapacidades()
        registrar_capacidades_operacionais(manager)
        return manager

    def test_conversa_textual_continua_sem_tool_call(self):
        cliente = ClienteFake([{"message": {"content": "Olá!"}}])
        dialogo = DialogoQwenNixal(cliente=cliente)
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=None):
            resultado = dialogo.responder("Oi")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["resposta"], "Olá!")
        self.assertEqual(resultado["quantidade_ferramentas"], 0)
        self.assertNotIn("tools", cliente.chamadas[0])

    def test_leitura_obter_hora_vai_e_volta_ao_modelo(self):
        cliente = ClienteFake([
            mensagem_tool("obter_hora", {}, "call-time"),
            {"message": {"content": "Consultei o horário atual."}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = self.manager()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            resultado = dialogo.responder("Que horas são?")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["quantidade_ferramentas"], 1)
        chamada = resultado["ferramentas_executadas"][0]
        self.assertEqual(chamada["name"], "obter_hora")
        self.assertTrue(chamada["ok"])
        self.assertTrue(any(
            item.get("role") == "tool"
            for item in cliente.chamadas[1]["messages"]
        ))

    def test_catalogo_padrao_exclui_dados_privados_e_mutacoes(self):
        dialogo = DialogoQwenNixal(cliente=ClienteFake([]))
        manager = self.manager()
        nomes = {
            item["function"]["name"]
            for item in dialogo._especificacoes_ferramentas(manager)
        }
        self.assertTrue({"obter_hora", "pesquisar_web", "consultar_metar_taf", "executar_diagnostico"} <= nomes)
        for proibida in (
            "listar_arquivos", "ler_arquivo", "ler_estado_corpo", "ler_memoria_corporal",
            "buscar_arquivos", "ler_arquivo_usuario", "consultar_emails_google",
            "ler_email_google", "consultar_agenda_google", "consultar_home_assistant",
            "listar_notas_lembretes", "salvar_nota", "criar_lembrete", "abrir_aplicativo",
        ):
            self.assertNotIn(proibida, nomes)

    def test_dados_privados_exigem_opt_in_de_ambiente(self):
        dialogo = DialogoQwenNixal(cliente=ClienteFake([]))
        manager = self.manager()
        with patch.dict(os.environ, {"NYXAL_ENABLE_PRIVATE_READ_TOOLS": "1"}):
            nomes = {
                item["function"]["name"]
                for item in dialogo._especificacoes_ferramentas(manager)
            }
        self.assertIn("listar_arquivos", nomes)
        self.assertIn("ler_arquivo", nomes)
        self.assertNotIn("salvar_nota", nomes)
        self.assertNotIn("criar_lembrete", nomes)
        self.assertNotIn("abrir_aplicativo", nomes)

    def test_mudancas_de_estado_sao_rejeitadas_mesmo_se_capacidade_existir(self):
        manager = self.manager()
        efeitos = []
        manager.registrar(
            nome="salvar_nota",
            descricao="não expor",
            objetivo="teste",
            exemplos=["teste"],
            funcao=lambda **kwargs: efeitos.append(kwargs) or {"gravou": True},
            argumentos={"titulo": {"tipo": "string", "obrigatorio": True}, "conteudo": {"tipo": "string", "obrigatorio": True}},
            dominios=["teste"],
            evidencias_dominio=["teste"],
        )
        dialogo = DialogoQwenNixal(cliente=ClienteFake([]))
        resultado = dialogo._executar_chamada_ferramenta(
            manager,
            mensagem_tool("salvar_nota", {"titulo": "segredo", "conteudo": "não gravar"})["message"]["tool_calls"][0],
            "Por favor, anote isso.",
        )
        self.assertFalse(resultado["ok"])
        self.assertIn("mutável desativada", resultado["resultado"])
        self.assertEqual(efeitos, [])

    def test_ferramenta_desconhecida_nao_e_executada(self):
        manager = self.manager()
        dialogo = DialogoQwenNixal(cliente=ClienteFake([]))
        resultado = dialogo._executar_chamada_ferramenta(
            manager,
            mensagem_tool("apagar_tudo", {})["message"]["tool_calls"][0],
            "Faça algo",
        )
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["resultado"], "Ferramenta não registrada/permitida.")

    def test_loop_de_ferramentas_tem_limite_global_de_chamadas(self):
        respostas = [mensagem_tool("obter_hora", {}, f"call-{i}") for i in range(dialogo_limite := 4)]
        respostas.append({"message": {"content": "Resposta final sem nova ferramenta."}})
        cliente = ClienteFake(respostas)
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = self.manager()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            resultado = dialogo.responder("Que horas são?")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["quantidade_ferramentas"], dialogo.MAX_TOOL_CALLS)
        self.assertEqual(len(cliente.chamadas), dialogo.MAX_TOOL_CALLS + 2)
        self.assertEqual(resultado["resposta"], "Resposta final sem nova ferramenta.")
        self.assertNotIn("tool_calls", cliente.chamadas[-1]["messages"][-1])

    def test_resultado_de_ferramenta_e_limitado(self):
        cliente = ClienteFake([mensagem_tool("obter_hora", {}), {"message": {"content": "final"}}])
        dialogo = DialogoQwenNixal(cliente=cliente)
        dialogo.MAX_TOOL_RESULT_CHARS = 32
        manager = self.manager()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            resultado = dialogo.responder("Que horas são?")
        self.assertLessEqual(
            len(resultado["ferramentas_executadas"][0]["resultado"]),
            dialogo.MAX_TOOL_RESULT_CHARS,
        )

    def test_argumentos_json_invalidos_sao_rejeitados(self):
        manager = self.manager()
        dialogo = DialogoQwenNixal(cliente=ClienteFake([]))
        resultado = dialogo._executar_chamada_ferramenta(
            manager,
            mensagem_tool("obter_hora", "{invalid")["message"]["tool_calls"][0],
            "Que horas são?",
        )
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["resultado"], "Argumentos JSON inválidos.")

    def test_falha_no_function_calling_regride_para_chat_textual(self):
        cliente = ClienteFake([
            TypeError("tools unsupported"),
            {"message": {"content": "fallback textual"}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = self.manager()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            resultado = dialogo.responder("Oi")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["resposta"], "fallback textual")
        self.assertEqual(resultado["quantidade_ferramentas"], 0)

    def test_pergunta_informativa_nao_concede_autorizacao_mutavel(self):
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
        self.assertTrue(
            DialogoQwenNixal._pedido_explicitamente_autorizou(
                "abrir_aplicativo", "Por favor, abra o navegador."
            )
        )

    def test_resposta_final_nao_afirma_execucao_sem_resultado(self):
        cliente = ClienteFake([
            mensagem_tool("apagar_tudo", {}),
            {"message": {"content": "A ferramenta não está permitida."}},
        ])
        dialogo = DialogoQwenNixal(cliente=cliente)
        manager = self.manager()
        with patch.object(dialogo, "_gerenciador_ferramentas", return_value=manager):
            resultado = dialogo.responder("Faça algo")
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["quantidade_ferramentas"], 1)
        self.assertFalse(resultado["ferramentas_executadas"][0]["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
