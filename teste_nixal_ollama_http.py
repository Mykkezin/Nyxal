from __future__ import annotations

import io
import json
import os
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

import nixal_ollama_http as engine


class TestOllamaHTTP(unittest.TestCase):
    def test_chat_envia_modelo_historico_tools_e_opcoes(self):
        response = io.BytesIO(b'{"message":{"role":"assistant","content":"oi"}}')
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://127.0.0.1:11434"}, clear=True):
            with patch.object(engine, "build_opener") as build:
                build.return_value.open.return_value = response
                result = engine.chat(
                    model="qwen2:7b",
                    messages=[{"role": "user", "content": "oi"}],
                    tools=[{"type": "function", "function": {"name": "hora"}}],
                    options={"temperature": 0.1},
                )
        self.assertEqual(result["message"]["content"], "oi")
        request = build.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "qwen2:7b")
        self.assertEqual(payload["tools"][0]["function"]["name"], "hora")
        self.assertEqual(payload["options"]["temperature"], 0.1)
        self.assertFalse(payload["stream"])

    def test_lista_modelos_sem_inferencia(self):
        response = io.BytesIO(b'{"models":[{"name":"qwen2:7b"},{"name":"nomic-embed-text:latest"}]}')
        with patch.object(engine, "build_opener") as build:
            build.return_value.open.return_value = response
            self.assertEqual(engine.OllamaHTTPClient().list_models(), ["qwen2:7b", "nomic-embed-text:latest"])
        request = build.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/tags")

    def test_catalogo_preserva_capacidades_reportadas_pelo_ollama(self):
        response = io.BytesIO(b'{"models":[{"name":"qwen2:7b","capabilities":["completion","tools"],"details":{"parameter_size":"7.6B"}}]}')
        with patch.object(engine, "build_opener") as build:
            build.return_value.open.return_value = response
            record = engine.OllamaHTTPClient().model_catalog()[0]
        self.assertEqual(record["capabilities"], ["completion", "tools"])
        self.assertEqual(record["details"]["parameter_size"], "7.6B")

    def test_streaming_decodifica_ndjson(self):
        class StreamingResponse:
            closed = False
            def __iter__(self):
                return iter([b'{"message":{"content":"a"}}\n', b'{"done":true}\n'])
            def close(self):
                self.closed = True
        response = StreamingResponse()
        with patch.object(engine, "build_opener") as build:
            build.return_value.open.return_value = response
            parts = list(engine.chat(model="qwen2:7b", messages=[{"role":"user","content":"x"}], stream=True))
        self.assertEqual(parts[0]["message"]["content"], "a")
        self.assertTrue(parts[1]["done"])
        self.assertTrue(response.closed)

    def test_http_error_nao_expoe_body(self):
        error = HTTPError("http://127.0.0.1:11434/api/chat", 500, "Failure", {}, io.BytesIO(b"secret-body"))
        with patch.object(engine, "build_opener") as build:
            build.return_value.open.side_effect = error
            with self.assertRaisesRegex(engine.OllamaHTTPError, "HTTP 500") as raised:
                engine.chat(model="qwen2:7b", messages=[{"role":"user","content":"x"}])
        self.assertNotIn("secret-body", str(raised.exception))

    def test_host_rejeita_credenciais_query_e_path(self):
        for value in ("http://user:secret@127.0.0.1:11434", "http://127.0.0.1:11434/?x=1", "http://127.0.0.1:11434/api"):
            with self.subTest(value=value), patch.dict(os.environ, {"OLLAMA_HOST": value}, clear=True):
                with self.assertRaises(engine.OllamaHTTPError):
                    engine._base_url()


if __name__ == "__main__":
    unittest.main(verbosity=2)
