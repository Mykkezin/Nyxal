#!/usr/bin/env python3
from __future__ import annotations

import base64
import unittest
from unittest.mock import patch

from nixal_integracao_gmail import IntegracaoGmailNixOS, SCOPES


class FakeRequest:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeMessages:
    def __init__(self):
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        return FakeRequest({"messages": [{"id": "m1"}]})

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        if kwargs.get("format") == "metadata":
            return FakeRequest({
                "id": kwargs["id"],
                "threadId": "t1",
                "labelIds": ["UNREAD"],
                "snippet": "Prévia segura",
                "payload": {"headers": [
                    {"name": "Subject", "value": "Assunto"},
                    {"name": "From", "value": "remetente@example.test"},
                    {"name": "Date", "value": "Fri, 09 Oct 2026 10:00:00 -0300"},
                ]},
            })
        return FakeRequest({
            "id": kwargs["id"],
            "threadId": "t1",
            "payload": {
                "mimeType": "text/plain",
                "headers": [{"name": "Subject", "value": "Assunto"}],
                "body": {"data": base64.urlsafe_b64encode("Corpo de teste".encode()).decode().rstrip("=")},
            },
        })


class FakeUsers:
    def __init__(self, messages):
        self._messages = messages

    def messages(self):
        return self._messages


class FakeService:
    def __init__(self, messages):
        self._messages = messages

    def users(self):
        return FakeUsers(self._messages)


class TestGmailReadonly(unittest.TestCase):
    def test_escopos_sao_somente_leitura(self):
        self.assertIn("https://www.googleapis.com/auth/gmail.readonly", SCOPES)
        self.assertIn("https://www.googleapis.com/auth/calendar.readonly", SCOPES)
        self.assertIn("https://www.googleapis.com/auth/contacts.readonly", SCOPES)
        self.assertIn("https://www.googleapis.com/auth/drive.metadata.readonly", SCOPES)
        self.assertTrue(all(scope.endswith(".readonly") for scope in SCOPES))

    def test_lista_mensagens_com_resumo_sem_alterar_estado(self):
        messages = FakeMessages()
        service = FakeService(messages)
        client = IntegracaoGmailNixOS()
        with patch.object(client, "_service", return_value=service):
            result = client.listar_mensagens("is:unread", 10)
        self.assertTrue(result["sucesso"])
        self.assertTrue(result["somente_leitura"])
        self.assertEqual(result["mensagens"][0]["assunto"], "Assunto")
        self.assertTrue(all(kind in {"list", "get"} for kind, _ in messages.calls))

    def test_leitura_do_corpo_textual(self):
        client = IntegracaoGmailNixOS()
        messages = FakeMessages()
        with patch.object(client, "_service", return_value=FakeService(messages)):
            result = client.obter_mensagem("m1")
        self.assertEqual(result["corpo_texto"], "Corpo de teste")
        self.assertTrue(result["somente_leitura"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
