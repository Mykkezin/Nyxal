#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import types
import unittest
from unittest.mock import patch

try:
    import ollama  # noqa: F401
except ImportError:
    ollama_stub = types.ModuleType("ollama")
    ollama_stub.chat = lambda **_kwargs: None
    sys.modules["ollama"] = ollama_stub

from nixal_amd_developer_cloud import AmdCloudChatClient, AmdDeveloperCloud
from nixal_dialogo_qwen import DialogoQwenNixal


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int = -1) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class AmdDeveloperCloudTest(unittest.TestCase):
    def test_unconfigured_status_does_not_expose_api_key(self) -> None:
        cloud = AmdDeveloperCloud(base_url="", api_key="secret-token", model="qwen-test")
        status = cloud.status()
        self.assertEqual(status["estado"], "nao_configurado")
        self.assertFalse(status["endpoint_configurado"])
        self.assertNotIn("secret-token", json.dumps(status))

    def test_base_url_adds_v1(self) -> None:
        cloud = AmdDeveloperCloud(base_url="http://127.0.0.1:8000")
        self.assertEqual(cloud.base_url, "http://127.0.0.1:8000/v1")

    def test_invalid_url_is_reported_without_crashing(self) -> None:
        cloud = AmdDeveloperCloud(base_url="file:///tmp/amd")
        self.assertEqual(cloud.status()["estado"], "configuracao_invalida")

    def test_cloud_status_selected_from_environment(self) -> None:
        with patch.dict("os.environ", {"NYXAL_LLM_PROVIDER": "amd_cloud"}):
            cloud = AmdDeveloperCloud(base_url="http://127.0.0.1:8000/v1")
            self.assertTrue(cloud.status()["selecionado_para_conversa"])

    def test_health_check_lists_models_without_credentials(self) -> None:
        cloud = AmdDeveloperCloud(
            base_url="http://127.0.0.1:8000/v1",
            api_key="secret-token",
            model="qwen-test",
        )
        fake = FakeResponse({"data": [{"id": "qwen-test"}, {"id": "llama-test"}]})
        with patch("nixal_amd_developer_cloud.urlopen", return_value=fake) as opened:
            result = cloud.verificar_conexao()

        self.assertTrue(result["sucesso"])
        self.assertEqual(result["modelos"], ["qwen-test", "llama-test"])
        self.assertNotIn("secret-token", json.dumps(result))
        request = opened.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")

    def test_chat_uses_openai_compatible_response_shape(self) -> None:
        cloud = AmdDeveloperCloud(
            base_url="http://127.0.0.1:8000/v1",
            api_key="secret-token",
            model="qwen-test",
        )
        fake = FakeResponse({
            "choices": [{"message": {"content": "Nyxal conectada à GPU AMD."}}]
        })
        with patch("nixal_amd_developer_cloud.urlopen", return_value=fake) as opened:
            result = AmdCloudChatClient(cloud).chat(
                model="ignored-model",
                messages=[{"role": "user", "content": "Teste"}],
                options={"temperature": 0.4},
            )

        self.assertEqual(
            result["message"]["content"],
            "Nyxal conectada à GPU AMD.",
        )
        request = opened.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "qwen-test")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["temperature"], 0.4)
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")

    def test_dialogue_selects_cloud_provider_when_configured(self) -> None:
        env = {
            "NYXAL_LLM_PROVIDER": "amd_cloud",
            "NYXAL_AMD_CLOUD_BASE_URL": "http://127.0.0.1:8000/v1",
            "NYXAL_AMD_CLOUD_MODEL": "amd-test-model",
        }
        with patch.dict(os.environ, env):
            dialogo = DialogoQwenNixal()
        self.assertIsInstance(dialogo.cliente, AmdCloudChatClient)
        self.assertEqual(dialogo.modelo, "amd-test-model")

    def test_chat_refuses_to_call_without_endpoint(self) -> None:
        cloud = AmdDeveloperCloud(base_url="")
        with self.assertRaisesRegex(RuntimeError, "BASE_URL_nao_configurada"):
            cloud.chat(model="qwen-test", messages=[{"role": "user", "content": "Oi"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
