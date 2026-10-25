#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import unittest
from unittest.mock import patch

import nixal_capacidade_visual as visual
from nixal_capacidade_visual import CapacidadeVisualGeminiNixOS


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 24)
JPEG_BYTES = b"\xff\xd8\xff" + (b"\x00" * 24)


class FakeResponse:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.data if size < 0 else self.data[:size]


def response_with_image(image_bytes: bytes = PNG_BYTES, mime_type: str = "image/png") -> dict:
    return {
        "steps": [{
            "type": "model_output",
            "content": [
                {"type": "text", "text": "Imagem concluída."},
                {
                    "type": "image",
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                },
            ],
        }],
        "status": "completed",
    }


class TestCapacidadeVisualGemini(unittest.TestCase):
    def test_exige_prompt(self):
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with self.assertRaises(ValueError):
                CapacidadeVisualGeminiNixOS().gerar_ou_editar("   ")

    def test_exige_chave(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                CapacidadeVisualGeminiNixOS().gerar_ou_editar("uma paisagem")

    def test_recusa_mime_nao_permitido(self):
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with self.assertRaises(ValueError):
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "editar",
                    imagem_base64=base64.b64encode(b"<svg/>").decode("ascii"),
                    mime_type="image/svg+xml",
                )

    def test_redirecionamento_nao_e_seguido_ao_conter_chave_gemini(self):
        request = visual.Request(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={"x-goog-api-key": "segredo-de-teste"},
        )
        handler = visual._RejectRedirects()
        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {"Location": "https://attacker.example/collect"},
            "https://attacker.example/collect",
        )
        self.assertIsNone(redirected)
        self.assertEqual(request.get_header("X-goog-api-key"), "segredo-de-teste")

    def test_recusa_conteudo_que_nao_corresponde_ao_mime(self):
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with self.assertRaisesRegex(ValueError, "não corresponde"):
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Editar a imagem",
                    imagem_base64=base64.b64encode(JPEG_BYTES).decode("ascii"),
                    mime_type="image/png",
                )

    def test_retorna_imagem_sem_guardar_upload_e_define_resolucao_padrao(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                result = CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma paisagem.")

        self.assertTrue(result["sucesso"])
        self.assertEqual(result["estado"], "imagem_gerada")
        self.assertEqual(result["mime_type"], "image/png")
        self.assertEqual(base64.b64decode(result["imagem_base64"]), PNG_BYTES)
        self.assertFalse(result["upload_salvo_no_servidor"])
        request = mocked.call_args.args[0]
        self.assertIn("x-goog-api-key", {key.lower() for key in request.headers})
        request_payload = json.loads(request.data.decode("utf-8"))
        self.assertFalse(request_payload["store"])
        self.assertEqual(request_payload["model"], "gemini-nano-banana-2.1")
        self.assertNotIn("generation_config", request_payload)
        self.assertEqual(request_payload["response_format"][1]["image_size"], "2K")
        self.assertIn("hierarquia visual clara", request_payload["input"][0]["text"])
        self.assertIn("Crie uma paisagem.", request_payload["input"][0]["text"])

    def test_nivel_explicito_high_e_enviado_na_configuracao_oficial(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "high",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma imagem simples.")

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["generation_config"], {"thinking_level": "high"})

    def test_auto_escolhe_high_para_prompt_com_texto_e_layout(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "auto",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Crie um infográfico de arquitetura com tipografia legível, texto exato "
                    "NYXAL e uma hierarquia visual clara."
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["generation_config"], {"thinking_level": "high"})

    def test_auto_preserva_nivel_padrao_para_prompt_simples(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "auto",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Uma flor amarela sobre fundo branco."
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["generation_config"], {"thinking_level": "medium"})

    def test_auto_nao_confunde_contexto_ou_dialogo_com_palavras_de_complexidade(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "auto",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Crie uma ilustração do diálogo entre duas pessoas em um contexto urbano, com marcação de coordenadas."
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["generation_config"], {"thinking_level": "medium"})

    def test_auto_usa_high_para_flash_image_quando_prompt_e_complexo(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3.1-flash-image",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "auto",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Crie um infográfico de arquitetura com tipografia legível e texto exato."
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["generation_config"], {"thinking_level": "high"})
        self.assertEqual(payload["model"], "gemini-3.1-flash-image")

    def test_auto_usa_minimal_para_prompt_simples_no_flash_image(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3.1-flash-image",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "auto",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar("Uma flor amarela em fundo branco.")

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["generation_config"], {"thinking_level": "minimal"})

    def test_recusa_nivel_de_raciocinio_nao_suportado_antes_da_chamada(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3.1-flash-lite-image",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "medium",
        }, clear=True):
            with patch("nixal_capacidade_visual._urlopen_no_redirect") as mocked:
                with self.assertRaisesRegex(ValueError, "não suporta o nível de raciocínio"):
                    CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma paisagem.")
        mocked.assert_not_called()

    def test_auto_e_rejeitado_para_modelo_sem_niveis_publicados(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "unknown-custom-image-model",
            "NYXAL_GEMINI_IMAGE_THINKING_LEVEL": "auto",
        }, clear=True):
            with patch("nixal_capacidade_visual._urlopen_no_redirect") as mocked:
                with self.assertRaisesRegex(ValueError, "não possui níveis de raciocínio configuráveis validados"):
                    CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma imagem complexa.")
        mocked.assert_not_called()

    def test_traduz_parametros_midjourney_em_controles_da_api(self):
        response = response_with_image()
        prompt = "Wallpaper vertical para celular --ar 9:16 --stylize 700 4K"
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(prompt)

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        image_format = payload["response_format"][1]
        self.assertEqual(image_format["aspect_ratio"], "9:16")
        self.assertEqual(image_format["image_size"], "4K")
        prepared_prompt = payload["input"][0]["text"]
        self.assertNotIn("--ar", prepared_prompt)
        self.assertNotIn("--stylize", prepared_prompt)
        self.assertIn("interpretação artística mais ousada", prepared_prompt)
        self.assertIn(prompt.split(" --ar")[0], prepared_prompt)

    def test_normaliza_proporcao_midjourney_com_resolucao_original(self):
        response = response_with_image()
        prompt = "A cinematic wallpaper --ar 1920:1080"
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(prompt)

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["response_format"][1]["aspect_ratio"], "16:9")
        self.assertNotIn("--ar", payload["input"][0]["text"])

    def test_cartaz_vertical_prefere_proporcao_de_impressao(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Crie um cartaz vertical para um festival de cinema."
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["response_format"][1]["aspect_ratio"], "2:3")

    def test_modelo_lite_usa_1k_por_padrao(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3.1-flash-lite-image",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar("Wallpaper vertical para celular.")

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        image_format = payload["response_format"][1]
        self.assertEqual(image_format["aspect_ratio"], "9:16")
        self.assertNotIn("image_size", image_format)

    def test_flash_image_suporta_saida_512px_sob_demanda(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3.1-flash-image",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Crie um thumbnail quadrado em 512px."
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["response_format"][1]["image_size"], "512")
        self.assertEqual(payload["response_format"][1]["aspect_ratio"], "1:1")

    def test_flash_image_normaliza_05k_para_enum_rest_512(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3.1-flash-image",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma imagem de perfil em 0.5K.")

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["response_format"][1]["image_size"], "512")

    def test_nano_banana_21_rejeita_512px_nao_suportado(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch("nixal_capacidade_visual._urlopen_no_redirect") as mocked:
                with self.assertRaisesRegex(ValueError, "não suporta saída em 512px"):
                    CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma imagem em 0.5K.")
        mocked.assert_not_called()

    def test_modelo_lite_rejeita_resolucao_4k_nao_suportada(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3.1-flash-lite-image",
        }, clear=True):
            with patch("nixal_capacidade_visual._urlopen_no_redirect") as mocked:
                with self.assertRaisesRegex(ValueError, "só gera imagens em 1K"):
                    CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie um wallpaper em 4K.")
        mocked.assert_not_called()

    def test_modelo_pro_recusa_proporcao_extrema_nao_suportada(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-3-pro-image",
        }, clear=True):
            with patch("nixal_capacidade_visual._urlopen_no_redirect") as mocked:
                with self.assertRaisesRegex(ValueError, "não suporta a proporção 1:4"):
                    CapacidadeVisualGeminiNixOS().gerar_ou_editar("Cartaz técnico --ar 1:4.")
        mocked.assert_not_called()

    def test_traduz_parametro_no_em_exclusoes_explicitas(self):
        response = response_with_image()
        prompt = "Crie uma foto de produto --no texto, marca-d'agua --ar 1:1"
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(prompt)

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        prepared_prompt = payload["input"][0]["text"]
        self.assertIn("não inclua texto, marca-d'agua", prepared_prompt)
        self.assertNotIn("--no", prepared_prompt)
        self.assertNotIn("--ar", prepared_prompt)
        self.assertEqual(payload["response_format"][1]["aspect_ratio"], "1:1")

    def test_rejeita_8k_em_vez_de_silenciosamente_downgradear(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch("nixal_capacidade_visual._urlopen_no_redirect") as mocked:
                with self.assertRaisesRegex(ValueError, "não oferece saída nativa em 8K"):
                    CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie um wallpaper 8K.")
        mocked.assert_not_called()

    def test_nao_confunde_history_com_story_vertical(self):
        response = response_with_image()
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Create an editorial illustration about the history of architecture."
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertNotIn("aspect_ratio", payload["response_format"][1])

    def test_edicao_preserva_areas_nao_solicitadas_e_nao_forca_tamanho(self):
        response = response_with_image()
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                result = CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Remova o fundo",
                    imagem_base64=base64.b64encode(PNG_BYTES).decode("ascii"),
                    mime_type="image/png",
                )

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["input"][0]["type"], "text")
        self.assertEqual(payload["input"][1]["type"], "image")
        self.assertFalse(payload["store"])
        self.assertNotIn("image_size", payload["response_format"][1])
        self.assertIn("aplique somente as mudanças pedidas", payload["input"][0]["text"])
        self.assertIn("Remova o fundo", payload["input"][0]["text"])
        self.assertEqual(result["estado"], "imagem_editada")

    def test_rejeita_imagem_de_resposta_com_base64_invalido(self):
        response = {
            "steps": [{
                "type": "model_output",
                "content": [{"type": "image", "mime_type": "image/png", "data": "not base64%%%"}],
            }],
        }
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ):
                with self.assertRaisesRegex(RuntimeError, "dados de imagem inválidos"):
                    CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma paisagem.")

    def test_prioriza_output_image_final_sobre_imagens_intermediarias(self):
        final_image = b"\x89PNG\r\n\x1a\n" + (b"F" * 24)
        response = response_with_image()
        response["output_image"] = {
            "mime_type": "image/png",
            "data": base64.b64encode(final_image).decode("ascii"),
        }
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ):
                result = CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma paisagem.")

        self.assertEqual(base64.b64decode(result["imagem_base64"]), final_image)

    def test_sem_output_image_seleciona_ultima_imagem_dos_steps(self):
        final_image = b"\x89PNG\r\n\x1a\n" + (b"L" * 24)
        response = {
            "steps": [
                {
                    "type": "model_output",
                    "content": [{
                        "type": "image",
                        "mime_type": "image/png",
                        "data": base64.b64encode(PNG_BYTES).decode("ascii"),
                    }],
                },
                {
                    "type": "model_output",
                    "content": [{
                        "type": "image",
                        "mime_type": "image/png",
                        "data": base64.b64encode(final_image).decode("ascii"),
                    }],
                },
            ],
        }
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ):
                result = CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma paisagem.")

        self.assertEqual(base64.b64decode(result["imagem_base64"]), final_image)

    def test_prompt_de_infografico_recebe_direcao_de_legibilidade(self):
        response = response_with_image()
        prompt = "Crie um infográfico com três etapas e os títulos exatos Reciclar, Reutilizar e Reduzir."
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(prompt)

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        prepared = payload["input"][0]["text"]
        self.assertIn("Para informação visual", prepared)
        self.assertIn("não invente métricas", prepared)
        self.assertIn(prompt, prepared)

    def test_prompt_de_logotipo_evita_mockups_nao_solicitados(self):
        response = response_with_image()
        prompt = "Crie um logotipo minimalista para uma marca de café."
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(prompt)

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        prepared = payload["input"][0]["text"]
        self.assertIn("Para a marca", prepared)
        self.assertIn("mockups de marca sem solicitação", prepared)

    def test_prompt_de_fotografia_de_produto_adiciona_direcao_de_estudio(self):
        response = response_with_image()
        prompt = "Fotografia de produto de uma caneca cerâmica azul sobre fundo neutro."
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch(
                "nixal_capacidade_visual._urlopen_no_redirect",
                return_value=FakeResponse(json.dumps(response).encode()),
            ) as mocked:
                CapacidadeVisualGeminiNixOS().gerar_ou_editar(prompt)

        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        prepared = payload["input"][0]["text"]
        self.assertIn("Para o produto", prepared)
        self.assertIn("sombras de contato plausíveis", prepared)

    def test_status_expoe_controles_sem_revelar_segredos(self):
        with patch.dict(os.environ, {}, clear=True):
            status = CapacidadeVisualGeminiNixOS().status()
        self.assertEqual(status["estado"], "configuracao_pendente")
        self.assertTrue(status["controles"]["proporcao_automatica"])
        self.assertEqual(status["nivel_raciocinio_configurado"], "padrao_do_provedor")
        self.assertIn("high", status["niveis_raciocinio_suportados"])
        flash_levels = visual.MODEL_THINKING_LEVELS["gemini-3.1-flash-image"]
        self.assertEqual(flash_levels, frozenset({"minimal", "high"}))
        self.assertEqual(visual.MODEL_DEFAULT_THINKING_LEVEL["gemini-3.1-flash-image"], "minimal")
        lite_levels = visual.MODEL_THINKING_LEVELS["gemini-3.1-flash-lite-image"]
        self.assertEqual(lite_levels, frozenset({"minimal", "high"}))
        self.assertNotIn("api_key", json.dumps(status).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
