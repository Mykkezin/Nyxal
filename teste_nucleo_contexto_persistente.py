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
from nixal_memoria_conhecimento import MemoriaConhecimentoNixal
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
        self.caminho_conhecimento = Path(self.tempdir.name) / "memoria_conhecimento_nixal.json"
        self.memoria_conhecimento = MemoriaConhecimentoNixal(self.caminho_conhecimento)

    def criar_nucleo(self, **kwargs) -> NucleoConversacionalNixal:
        kwargs.setdefault("memoria_conhecimento", self.memoria_conhecimento)
        return NucleoConversacionalNixal(**kwargs)

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
        nucleo = self.criar_nucleo(
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

    def test_core_injeta_conhecimento_candidato_relevante_com_proveniencia(self) -> None:
        candidato = {
            "texto": "A estratégia de cache do motor local usa invalidação por versão e TTL.",
            "tipo": "arquitetura",
            "origem": {"estado": "suportada", "indice_avaliacao": 7, "fonte": "teste-cache"},
            "conhecimento_permanente": False,
            "gravado": False,
        }
        self.assertTrue(self.memoria_conhecimento.registrar(candidato)["sucesso"])
        cliente = FakeChatClient()
        dialogo = DialogoQwenNixal(modelo="fixture-model", cliente=cliente)
        nucleo = self.criar_nucleo(
            dialogo=dialogo,
            memoria_investigacao=self.memoria,
            contexto_historico_relevante=self.contexto,
        )

        consulta = "Onde paramos na estratégia de cache do motor local?"
        resposta = nucleo.processar(
            nucleo.interface.criar_entrada(consulta, sessao="sessao-candidato-relevante")
        )
        mensagens = cliente.calls[0]["messages"]
        texto_usuario = "\\n".join(
            item["content"] for item in mensagens if item["role"] == "user"
        )
        self.assertIn("CANDIDATOS DE CONHECIMENTO", texto_usuario)
        self.assertIn("invalidação por versão e TTL", texto_usuario)
        self.assertIn("nao_equivale_a_verdade", texto_usuario)
        self.assertNotIn('"conhecimento_permanente":true', texto_usuario)
        metadados = resposta["valor"]["conhecimento_candidato_persistido"]
        self.assertTrue(metadados["consultado"])
        self.assertEqual(metadados["quantidade"], 1)
        self.assertFalse(metadados["conhecimento_permanente"])
        self.assertTrue(metadados["registros"])

    def test_core_nao_injeta_conhecimento_candidato_irrelevante(self) -> None:
        candidato = {
            "texto": "A paleta do personagem usa verde esmeralda e dourado.",
            "tipo": "arte",
            "origem": {"estado": "suportada", "indice_avaliacao": 2},
            "conhecimento_permanente": False,
            "gravado": False,
        }
        self.assertTrue(self.memoria_conhecimento.registrar(candidato)["sucesso"])
        cliente = FakeChatClient()
        nucleo = self.criar_nucleo(
            dialogo=DialogoQwenNixal(modelo="fixture-model", cliente=cliente),
            memoria_investigacao=self.memoria,
            contexto_historico_relevante=self.contexto,
        )
        resposta = nucleo.processar(
            nucleo.interface.criar_entrada(
                "Onde paramos no roteamento de consultas SQL?", sessao="sessao-candidato-irrelevante"
            )
        )
        texto_usuario = "\\n".join(
            item["content"] for item in cliente.calls[0]["messages"] if item["role"] == "user"
        )
        self.assertNotIn("CANDIDATOS DE CONHECIMENTO", texto_usuario)
        self.assertEqual(resposta["valor"]["conhecimento_candidato_persistido"]["quantidade"], 0)

    def test_core_preserva_memoria_candidata_corrompida_e_nao_injeta_candidatos(self) -> None:
        caminho = Path(self.tempdir.name) / "memoria_conhecimento_corrompida.json"
        original = '{"versao":'
        caminho.write_text(original, encoding="utf-8")
        memoria_corrompida = MemoriaConhecimentoNixal(caminho)
        cliente = FakeChatClient()
        nucleo = self.criar_nucleo(
            dialogo=DialogoQwenNixal(modelo="fixture-model", cliente=cliente),
            memoria_investigacao=self.memoria,
            contexto_historico_relevante=self.contexto,
            memoria_conhecimento=memoria_corrompida,
        )
        resposta = nucleo.processar(
            nucleo.interface.criar_entrada(
                "Onde paramos nas decisões de cache do motor local?", sessao="sessao-conhecimento-corrompido"
            )
        )
        metadados = resposta["valor"]["conhecimento_candidato_persistido"]
        self.assertEqual(metadados["estado"], "memoria_degradada")
        self.assertEqual(metadados["quantidade"], 0)
        self.assertEqual(caminho.read_text(encoding="utf-8"), original)
        texto_usuario = "\\n".join(
            item["content"] for item in cliente.calls[0]["messages"] if item["role"] == "user"
        )
        self.assertNotIn("CANDIDATOS DE CONHECIMENTO", texto_usuario)

    def test_core_compartilha_catalogo_de_capacidades_com_dialogo(self) -> None:
        cliente = FakeChatClient()
        dialogo = DialogoQwenNixal(modelo="fixture-model", cliente=cliente)
        # Simula um diálogo já inicializado com outro catálogo.
        dialogo.gerenciador_capacidades = Mock()
        dialogo._ferramentas_operacionais_registradas = True

        nucleo = self.criar_nucleo(dialogo=dialogo)

        self.assertIs(nucleo.dialogo, dialogo)
        self.assertIs(
            dialogo.gerenciador_capacidades,
            nucleo.agente.capacidades,
        )
        self.assertFalse(dialogo._ferramentas_operacionais_registradas)

    def test_core_ignores_legacy_remote_provider_and_preserves_canonical_session_history(self) -> None:
        cliente = FakeChatClient()
        dialogo = DialogoQwenNixal(modelo="fixture-model", cliente=cliente)
        hub = Mock()
        dialogo.agent_hub = hub
        memoria_conversacional = MemoriaConversacionalNixal()
        nucleo = self.criar_nucleo(
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
        resposta_local = (
            "Encontrei uma investigação anterior; ela é contexto histórico, "
            "não confirmação do estado atual."
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
        self.assertEqual(primeira["resposta"], resposta_local)
        self.assertEqual(len(cliente.calls), 1)
        self.assertEqual(cliente.calls[0]["model"], "fixture-model")
        self.assertIn('"cpu_percent":12.5', cliente.calls[0]["messages"][0]["content"])
        texto_usuario_primeiro = "\n".join(
            item["content"]
            for item in cliente.calls[0]["messages"]
            if item["role"] == "user"
        )
        self.assertIn("CONTEXTO DE INVESTIGAÇÕES ANTERIORES", texto_usuario_primeiro)
        # Seleções legadas como OpenAI/Gemini não reativam o hub externo.
        hub.responder.assert_not_called()

        segunda_mensagem = "E qual é o próximo passo?"
        segunda_entrada = nucleo.interface.criar_entrada(
            segunda_mensagem, sessao=sessao
        )
        segunda_entrada["valor"]["opcoes_dialogo"] = {
            "provedor": "openai",
            "contexto_sistema": contexto_sistema,
        }
        segunda = nucleo.processar(segunda_entrada)

        self.assertEqual(segunda["valor"]["modo"], "resposta_conversacional")
        self.assertEqual(segunda["resposta"], resposta_local)
        self.assertEqual(len(cliente.calls), 2)
        historico_dialogo = cliente.calls[1]["messages"]
        self.assertIn(
            {"role": "user", "content": primeira_mensagem},
            historico_dialogo,
        )
        self.assertIn(
            {"role": "assistant", "content": resposta_local},
            historico_dialogo,
        )
        self.assertEqual(hub.responder.call_count, 0)

        historico_canonico = memoria_conversacional.obter(sessao)["mensagens"]
        self.assertEqual(
            [item["papel"] for item in historico_canonico],
            ["user", "assistant", "user", "assistant"],
        )
        self.assertEqual(
            [item["texto"] for item in historico_canonico][-2:],
            [segunda_mensagem, resposta_local],
        )

    def test_memoria_corrompida_nao_e_classificada_como_historico_ausente(self) -> None:
        caminho_corrompido = Path(self.tempdir.name) / "memoria_corrompida.json"
        conteudo_original = '{"versao":'
        caminho_corrompido.write_text(conteudo_original, encoding="utf-8")

        memoria_corrompida = MemoriaInvestigacaoNixal(caminho_corrompido)
        contexto_corrompido = ContextoHistoricoRelevanteNixal(memoria_corrompida)
        cliente = FakeChatClient()
        dialogo = DialogoQwenNixal(modelo="fixture-model", cliente=cliente)
        nucleo = self.criar_nucleo(
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

    def test_sanitizacao_de_contexto_redige_bearer_e_token_generico(self) -> None:
        entrada = (
            "Authorization: Bearer bearer_secret_123 "
            "token=plain_secret_456 refresh_token=refresh_secret_789"
        )
        saida = NucleoConversacionalNixal._texto_curto_contexto(entrada)
        self.assertNotIn("bearer_secret_123", saida)
        self.assertNotIn("plain_secret_456", saida)
        self.assertNotIn("refresh_secret_789", saida)
        self.assertIn("Bearer [REDACTED]", saida)
        self.assertIn("token=[REDACTED]", saida)
        self.assertIn("authorization=[REDACTED]", saida)

    def test_consulta_lexical_rejeita_limite_invalido(self) -> None:
        for limite in (0, -1, 6, True, "3"):
            with self.subTest(limite=limite):
                resultado = self.contexto.analisar_consulta("runner privado", limite=limite)
                self.assertIs(resultado.get("sucesso"), False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
