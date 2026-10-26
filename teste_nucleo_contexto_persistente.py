#!/usr/bin/env python3
"""Regressões do uso read-only da memória de investigação no diálogo."""
from __future__ import annotations

import sys
import tempfile
import types
import unittest
from unittest.mock import Mock
from pathlib import Path

# O teste usa o adaptador de diálogo com um cliente falso; não inicia um modelo.
sys.modules.setdefault("ollama", types.SimpleNamespace())

from nixal_contexto_historico_relevante import ContextoHistoricoRelevanteNixal
from nixal_dialogo_qwen import DialogoQwenNixal
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal
from nixal_memoria_conversacional import MemoriaConversacionalNixal
from nixal_nucleo_conversacional import NucleoConversacionalNixal


class FakeChatClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "message": {
                "content": (
                    "Encontrei uma investigação anterior; ela é contexto histórico, "
                    "não confirmação do estado atual."
                )
            }
        }


def sample_cycle() -> dict:
    return {
        "necessidade": "Diagnosticar o runner privado do GitHub Actions.",
        "pergunta": "Por que a CI privada termina antes do primeiro step?",
        "hipotese": (
            "O workflow privado do GitHub Actions falha antes de alocar runner. "
            "access_token=abc123"
        ),
        "estado_atual": "provisoria",
        "historico": [
            {"evento": "observacao", "descricao": "runner_id=0; steps vazios"}
        ],
        "testes": [
            {"nome": "runner privado", "estado": "nao_verificado"}
        ],
        "avaliacoes": [
            {"criterio": "execucao_real", "estado": "inconclusivo"}
        ],
        "conhecimento_permanente": False,
    }


class TesteContextoInvestigacaoPersistido(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.caminho = Path(self.tempdir.name) / "memoria_investigacao_nixal.json"
        self.memoria = MemoriaInvestigacaoNixal(self.caminho)
        registro = self.memoria.registrar(sample_cycle())
        self.assertIs(registro.get("sucesso"), True)
        self.contexto = ContextoHistoricoRelevanteNixal(self.memoria)

    def test_ciclo_helper_retorna_copia_e_rejeita_registro_invalido(self) -> None:
        ciclo = sample_cycle()
        resultado = self.contexto._ciclo({"id": "registro-teste", "ciclo": ciclo})
        self.assertEqual(resultado, ciclo)
        self.assertIsNot(resultado, ciclo)
        resultado["necessidade"] = "alteração de teste"
        self.assertNotEqual(ciclo["necessidade"], resultado["necessidade"])
        self.assertIsNone(self.contexto._ciclo({"id": "sem-ciclo"}))
        self.assertIsNone(self.contexto._ciclo(None))

    def test_consulta_lexical_recupera_registro_com_proveniencia(self) -> None:
        resultado = self.contexto.analisar_consulta(
            "Onde paramos na investigação do runner privado do GitHub Actions?",
            limite=3,
        )
        self.assertIs(resultado.get("sucesso"), True)
        valor = resultado.get("valor", {})
        self.assertTrue(valor.get("historico_encontrado"))
        self.assertEqual(valor.get("quantidade"), 1)
        item = valor["contextos"][0]
        self.assertTrue(item["status_epistemico"]["nao_equivale_a_verdade"])
        self.assertTrue(item["origem_historica"]["id"])

    def test_consulta_sem_sobreposicao_nao_injeta_memoria_irrelevante(self) -> None:
        resultado = self.contexto.analisar_consulta(
            "Receita de bolo de chocolate com farinha.",
            limite=3,
        )
        self.assertIs(resultado.get("sucesso"), True)
        self.assertFalse(resultado["valor"]["historico_encontrado"])
        self.assertEqual(resultado["valor"]["contextos"], [])

    def test_core_recarrega_memoria_e_injeta_contexto_como_dado_nao_confiavel(self) -> None:
        cliente = FakeChatClient()
        dialogo = DialogoQwenNixal(modelo="fixture-model", cliente=cliente)
        nucleo = NucleoConversacionalNixal(
            dialogo=dialogo,
            memoria_investigacao=self.memoria,
            contexto_historico_relevante=self.contexto,
        )
        consulta = "Onde paramos na investigação do runner privado do GitHub Actions?"
        resposta = nucleo.processar(
            nucleo.interface.criar_entrada(consulta, sessao="sessao-teste-duravel")
        )

        self.assertEqual(resposta["estado"], "resposta_conversacional")
        metadados = resposta["valor"]["contexto_historico_persistido"]
        self.assertTrue(metadados["consultado"])
        self.assertEqual(metadados["quantidade"], 1)
        self.assertTrue(metadados["registros"])

        mensagens = cliente.calls[0]["messages"]
        self.assertIn("dado histórico não confiável", mensagens[0]["content"])
        texto_usuario = "\n".join(
            item["content"] for item in mensagens if item["role"] == "user"
        )
        self.assertIn(consulta, texto_usuario)
        self.assertIn("CONTEXTO DE INVESTIGAÇÕES ANTERIORES", texto_usuario)
        self.assertIn("runner privado", texto_usuario)
        self.assertIn("access_token=[REDACTED]", texto_usuario)
        self.assertNotIn("abc123", texto_usuario)

    def test_core_routes_explicit_provider_through_canonical_session_history(self) -> None:
        cliente = FakeChatClient()
        dialogo = DialogoQwenNixal(modelo="fixture-model", cliente=cliente)
        hub = Mock()
        hub.responder.return_value = {
            "sucesso": True,
            "estado": "resposta_gerada",
            "provedor": "openai",
            "resposta": "Resposta remota de teste.",
            "roteamento": {"classe": "conhecimento_geral", "provedor": "openai"},
        }
        dialogo.agent_hub = hub
        memoria_conversacional = MemoriaConversacionalNixal()
        nucleo = NucleoConversacionalNixal(
            dialogo=dialogo,
            memoria_conversacional=memoria_conversacional,
            memoria_investigacao=self.memoria,
            contexto_historico_relevante=self.contexto,
        )
        sessao = "sessao-provider-core"
        contexto_sistema = {"observabilidade": {"cpu_percent": 12.5}}
        primeira_mensagem = (
            "Onde paramos na investigação do runner privado do GitHub Actions?"
        )

        entrada = nucleo.interface.criar_entrada(
            primeira_mensagem, sessao=sessao
        )
        entrada["valor"]["opcoes_dialogo"] = {
            "provedor": "openai",
            "contexto_sistema": contexto_sistema,
        }
        primeira = nucleo.processar(entrada)

        self.assertEqual(primeira["valor"]["modo"], "resposta_conversacional")
        self.assertEqual(primeira["resposta"], "Resposta remota de teste.")
        kwargs = hub.responder.call_args.kwargs
        self.assertEqual(kwargs["provedor"], "openai")
        self.assertEqual(kwargs["sessao"], sessao)
        self.assertEqual(kwargs["contexto_sistema"], contexto_sistema)

        segunda_entrada = nucleo.interface.criar_entrada(
            "E qual é o próximo passo?", sessao=sessao
        )
        segunda_entrada["valor"]["opcoes_dialogo"] = {
            "provedor": "openai",
            "contexto_sistema": contexto_sistema,
        }
        segunda = nucleo.processar(segunda_entrada)
        self.assertEqual(segunda["valor"]["modo"], "resposta_conversacional")

        historico_remoto = hub.responder.call_args.kwargs["historico_externo"]
        self.assertIn(
            {"role": "user", "content": primeira_mensagem},
            historico_remoto,
        )
        self.assertIn(
            {"role": "assistant", "content": "Resposta remota de teste."},
            historico_remoto,
        )

        historico_canonico = memoria_conversacional.obter(sessao)["mensagens"]
        self.assertEqual(
            [item["papel"] for item in historico_canonico],
            ["user", "assistant", "user", "assistant"],
        )
        self.assertEqual(
            [item["texto"] for item in historico_canonico][-2:],
            ["E qual é o próximo passo?", "Resposta remota de teste."],
        )
        self.assertEqual(hub.responder.call_count, 2)
        # O núcleo fornece o histórico ao hub; a memória paralela do hub não deve
        # registrar novamente os mesmos turnos quando historico_externo é usado.

    def test_memoria_corrompida_nao_e_classificada_como_historico_ausente(self) -> None:
        caminho_corrompido = Path(self.tempdir.name) / "memoria_corrompida.json"
        conteudo_original = '{"versao":'
        caminho_corrompido.write_text(conteudo_original, encoding="utf-8")

        memoria_corrompida = MemoriaInvestigacaoNixal(caminho_corrompido)
        contexto_corrompido = ContextoHistoricoRelevanteNixal(memoria_corrompida)
        cliente = FakeChatClient()
        dialogo = DialogoQwenNixal(modelo="fixture-model", cliente=cliente)
        nucleo = NucleoConversacionalNixal(
            dialogo=dialogo,
            memoria_investigacao=memoria_corrompida,
            contexto_historico_relevante=contexto_corrompido,
        )

        consulta = "Onde paramos na investigação do runner privado do GitHub Actions?"
        resposta = nucleo.processar(
            nucleo.interface.criar_entrada(consulta, sessao="sessao-memoria-corrompida")
        )

        metadados = resposta["valor"]["contexto_historico_persistido"]
        self.assertTrue(metadados["consultado"])
        self.assertEqual(metadados["estado"], "memoria_degradada")
        self.assertEqual(metadados["quantidade"], 0)
        self.assertEqual(metadados["registros"], [])
        mensagens = cliente.calls[0]["messages"]
        texto_usuario = "\\n".join(
            item["content"] for item in mensagens if item["role"] == "user"
        )
        self.assertNotIn("CONTEXTO DE INVESTIGAÇÕES ANTERIORES", texto_usuario)
        self.assertEqual(caminho_corrompido.read_text(encoding="utf-8"), conteudo_original)

    def test_consulta_lexical_rejeita_limite_invalido(self) -> None:
        for limite in (0, -1, 6, True, "3"):
            with self.subTest(limite=limite):
                resultado = self.contexto.analisar_consulta("runner privado", limite=limite)
                self.assertIs(resultado.get("sucesso"), False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
