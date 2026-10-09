#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import unittest
from unittest.mock import patch

from nixal_capacidade_visual import CapacidadeVisualGeminiNixOS


class FakeResponse:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.data if size < 0 else self.data[:size]


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
                    "editar", imagem_base64=base64.b64encode(b"x").decode(), mime_type="image/svg+xml"
                )

    def test_retorna_imagem_sem_guardar_upload(self):
        response = {
            "steps": [{
                "type": "model_output",
                "content": [
                    {"type": "text", "text": "Imagem concluída."},
                    {"type": "image", "mime_type": "image/png", "data": base64.b64encode(b"png").decode()},
                ],
            }],
            "status": "completed",
        }
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_GEMINI_IMAGE_MODEL": "gemini-nano-banana-2.1",
        }, clear=True):
            with patch("nixal_capacidade_visual.urlopen", return_value=FakeResponse(json.dumps(response).encode())) as mocked:
                result = CapacidadeVisualGeminiNixOS().gerar_ou_editar("Crie uma paisagem.")
        self.assertTrue(result["sucesso"])
        self.assertEqual(result["estado"], "imagem_gerada")
        self.assertEqual(result["mime_type"], "image/png")
        self.assertEqual(base64.b64decode(result["imagem_base64"]), b"png")
        self.assertFalse(result["upload_salvo_no_servidor"])
        request = mocked.call_args.args[0]
        self.assertIn("x-goog-api-key", {key.lower() for key in request.headers})
        request_payload = json.loads(request.data.decode("utf-8"))
        self.assertFalse(request_payload["store"])
        self.assertEqual(request_payload["model"], "gemini-nano-banana-2.1")

    def test_edicao_envia_texto_antes_da_imagem_sem_armazenar_interacao(self):
        response = {
            "steps": [{
                "type": "model_output",
                "content": [{"type": "image", "mime_type": "image/png", "data": base64.b64encode(b"out").decode()}],
            }],
        }
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            with patch("nixal_capacidade_visual.urlopen", return_value=FakeResponse(json.dumps(response).encode())) as mocked:
                result = CapacidadeVisualGeminiNixOS().gerar_ou_editar(
                    "Remova o fundo",
                    imagem_base64=base64.b64encode(b"source").decode(),
                    mime_type="image/png",
                )
        payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["input"][0]["type"], "text")
        self.assertEqual(payload["input"][1]["type"], "image")
        self.assertFalse(payload["store"])
        self.assertEqual(result["estado"], "imagem_editada")

    def test_status_nao_confunde_configuracao_com_chave(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(CapacidadeVisualGeminiNixOS().status()["estado"], "configuracao_pendente")


if __name__ == "__main__":
    unittest.main(verbosity=2)
