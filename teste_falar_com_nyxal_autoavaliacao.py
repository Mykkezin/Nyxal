"""Testes offline para a ferramenta de autoavaliação local da Nyxal."""
from __future__ import annotations

import json
import os
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import falar_com_nyxal_autoavaliacao as ferramenta


class FakeResponse:
    def __init__(self, payload, status=200):
        self.data = json.dumps(payload).encode("utf-8")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.data if size < 0 else self.data[:size]


class TesteAutoavaliacaoLocal(unittest.TestCase):
    def test_url_permanece_em_loopback(self):
        self.assertEqual(
            ferramenta.loopback_url(8010),
            "http://127.0.0.1:8010/api/agent/chat",
        )

    def test_portas_invalidas_sao_rejeitadas(self):
        for porta in (0, -1, 65536, True, "8010"):
            with self.subTest(porta=porta):
                with self.assertRaises(ValueError):
                    ferramenta.loopback_url(porta)

    def test_extrai_resposta_de_envelope_aninhado(self):
        resultado = ferramenta.extrair_resposta({
            "sucesso": True,
            "valor": {"resultado": {"resposta": "Análise real"}},
        })
        self.assertEqual(resultado, "Análise real")

    def test_resposta_ausente_e_rejeitada(self):
        with self.assertRaises(ValueError):
            ferramenta.extrair_resposta({"sucesso": True, "estado": "ok"})

    def test_requisicao_envia_provedor_nyxal_e_sessao_sem_mudar_host(self):
        fake = FakeResponse({
            "sucesso": True,
            "estado": "conversa_processada",
            "resposta": "Nyxal responde",
            "sessao": "sessao-retornada",
        })
        with patch.object(ferramenta, "urlopen", return_value=fake) as chamada:
            resultado = ferramenta.chamar_nyxal(
                "Qual é o principal problema?",
                sessao="sessao-local",
                port=8010,
                timeout=5,
            )
        request = chamada.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "http://127.0.0.1:8010/api/agent/chat")
        self.assertEqual(body["provedor"], "nyxal")
        self.assertEqual(body["sessao"], "sessao-local")
        self.assertEqual(resultado["resposta"], "Nyxal responde")
        self.assertEqual(resultado["sessao"], "sessao-retornada")

    def test_token_e_enviado_apenas_no_cabecalho(self):
        fake = FakeResponse({"resposta": "ok", "sessao": "s"})
        with patch.dict(os.environ, {"NYXAL_API_TOKEN": "segredo-de-teste"}):
            with patch.object(ferramenta, "urlopen", return_value=fake) as chamada:
                ferramenta.chamar_nyxal("teste", sessao="s", port=8010, timeout=5)
        request = chamada.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer segredo-de-teste")
        self.assertNotIn("segredo-de-teste", request.data.decode("utf-8"))

    def test_envelope_de_erro_da_api_nao_vira_opiniao_da_nyxal(self):
        fake = FakeResponse({
            "sucesso": False,
            "estado": "erro_ao_processar_conversa",
            "resposta": "A Nyxal não conseguiu processar a mensagem.",
        })
        with patch.object(ferramenta, "urlopen", return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "api_nyxal_reportou_falha"):
                ferramenta.chamar_nyxal("autoavaliação", sessao="s", port=8010, timeout=5)

    def test_payload_grande_e_recusado(self):
        raw = b"x" * (ferramenta.MAX_RESPONSE_BYTES + 1)
        fake = FakeResponse({})
        fake.data = raw
        with patch.object(ferramenta, "urlopen", return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "excede_limite"):
                ferramenta.chamar_nyxal("teste", sessao="s", port=8010, timeout=5)

    def test_saida_e_criada_com_permissao_restrita_e_sem_sobrescrever(self):
        with tempfile.TemporaryDirectory() as directory:
            destino = Path(directory) / "resultado.json"
            ferramenta.salvar_saida(str(destino), {"turnos": []})
            self.assertEqual(destino.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(destino.read_text()), {"turnos": []})
            with self.assertRaises(FileExistsError):
                ferramenta.salvar_saida(str(destino), {"turnos": [1]})

    def test_main_executes_three_turns_and_carries_answers_forward(self):
        responses = [
            {"resposta": "Problema: runner privado não inicia.", "sessao": "s1",
             "estado_api": "ok", "sucesso_api": True},
            {"resposta": "H1: verificar configuração e uso.", "sessao": "s2",
             "estado_api": "ok", "sucesso_api": True},
            {"resposta": "Runner ainda não resolvido.", "sessao": "s3",
             "estado_api": "ok", "sucesso_api": True},
        ]
        with patch.object(ferramenta, "chamar_nyxal", side_effect=responses) as call:
            with patch("builtins.print"):
                codigo = ferramenta.main([])
        self.assertEqual(codigo, 0)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(call.call_args_list[0].args[0], ferramenta.PROMPT_AUTOAVALIACAO)
        self.assertIn("Problema: runner privado não inicia.", call.call_args_list[1].args[0])
        self.assertIn("H1: verificar configuração e uso.", call.call_args_list[2].args[0])
        self.assertEqual(call.call_args_list[0].kwargs["port"], 8010)
        self.assertEqual(call.call_args_list[1].kwargs["sessao"], "s1")
        self.assertEqual(call.call_args_list[2].kwargs["sessao"], "s2")

    def test_main_nao_fabrica_resposta_quando_api_local_falha(self):
        errors = io.StringIO()
        with patch.object(ferramenta, "chamar_nyxal", side_effect=RuntimeError("api_local_indisponivel")):
            with redirect_stderr(errors):
                codigo = ferramenta.main([])
        self.assertEqual(codigo, 2)
        self.assertIn("Nyxal não respondeu", errors.getvalue())
        self.assertNotIn("RESPOSTA REAL DA NYXAL", errors.getvalue())

    def test_prompts_exigem_evidencia_e_separam_plano_de_execucao(self):
        self.assertIn("Não invente", ferramenta.PROMPT_AUTOAVALIACAO)
        self.assertIn("H1", ferramenta.PROMPT_AUTOAPERFEICOAMENTO)
        self.assertIn("não execute ações", ferramenta.PROMPT_AUTOAPERFEICOAMENTO.lower())
        self.assertIn("não diga que o runner privado foi corrigido", ferramenta.PROMPT_VERIFICACAO.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
