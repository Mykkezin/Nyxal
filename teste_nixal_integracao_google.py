#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from nixal_integracao_gmail import (
    IntegracaoGmailNixOS,
    SCOPES,
)


class TestGoogleWorkspaceReadOnly(unittest.TestCase):
    def test_status_normaliza_escopos_string_com_espacos(self):
        with tempfile.TemporaryDirectory() as folder:
            client = Path(folder) / "oauth.json"
            token = Path(folder) / "token.json"
            client.write_text("{}", encoding="utf-8")
            token.write_text(
                json.dumps({"scopes": f"{SCOPES[0]} {SCOPES[2]}"}),
                encoding="utf-8",
            )
            with (
                patch("nixal_integracao_gmail.CLIENT_FILE", client),
                patch("nixal_integracao_gmail.TOKEN_FILE", token),
                patch.object(IntegracaoGmailNixOS, "_dependencies_available", return_value=True),
            ):
                status = IntegracaoGmailNixOS().status()
        self.assertEqual(status["escopos_ausentes"], [SCOPES[1], SCOPES[3]])

    def test_status_detecta_token_gmail_apenas_com_escopos_ausentes(self):
        with tempfile.TemporaryDirectory() as folder:
            client = Path(folder) / "oauth.json"
            token = Path(folder) / "token.json"
            client.write_text("{}", encoding="utf-8")
            token.write_text(
                json.dumps({"scopes": [SCOPES[0], "", f"{SCOPES[1]} {SCOPES[2]}", 123, None]}),
                encoding="utf-8",
            )
            with (
                patch("nixal_integracao_gmail.CLIENT_FILE", client),
                patch("nixal_integracao_gmail.TOKEN_FILE", token),
                patch.object(IntegracaoGmailNixOS, "_dependencies_available", return_value=True),
            ):
                status = IntegracaoGmailNixOS().status()
        self.assertEqual(status["estado"], "configuracao_pendente")
        self.assertEqual(status["escopos_ausentes"], [SCOPES[3]])
        self.assertTrue(status["somente_leitura"])
        self.assertFalse(status["pode_enviar_email"])

    def test_credentials_recebe_escopos_limpos_antes_do_refresh(self):
        escopos_brutos = [
            SCOPES[0],
            "",
            f"{SCOPES[1]} {SCOPES[2]}",
            123,
            None,
            SCOPES[3],
        ]
        escopos_esperados = sorted(SCOPES)
        token_info = {
            "token": "access-token",
            "refresh_token": "refresh-token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "scopes": escopos_brutos,
        }

        credenciais = MagicMock()
        credenciais.scopes = escopos_esperados
        credenciais.expired = True
        credenciais.refresh_token = "refresh-token"
        credenciais.valid = True
        # Imita o uso de scopes pelo refresh: valores não string causariam TypeError.
        credenciais.refresh.side_effect = (
            lambda _request: " ".join(credenciais.scopes)
        )
        credenciais.to_json.return_value = json.dumps(
            {"scopes": credenciais.scopes}
        )

        pacote_google = ModuleType("google")
        pacote_google.__path__ = []
        pacote_auth = ModuleType("google.auth")
        pacote_auth.__path__ = []
        pacote_transport = ModuleType("google.auth.transport")
        pacote_transport.__path__ = []
        modulo_requests = ModuleType("google.auth.transport.requests")
        modulo_requests.Request = MagicMock(name="GoogleRequest")
        pacote_oauth2 = ModuleType("google.oauth2")
        pacote_oauth2.__path__ = []
        modulo_credentials = ModuleType("google.oauth2.credentials")
        classe_credentials = MagicMock(name="Credentials")
        classe_credentials.from_authorized_user_info.return_value = credenciais
        modulo_credentials.Credentials = classe_credentials

        pacote_google.auth = pacote_auth
        pacote_auth.transport = pacote_transport
        pacote_transport.requests = modulo_requests
        pacote_google.oauth2 = pacote_oauth2
        pacote_oauth2.credentials = modulo_credentials

        modulos_google = {
            "google": pacote_google,
            "google.auth": pacote_auth,
            "google.auth.transport": pacote_transport,
            "google.auth.transport.requests": modulo_requests,
            "google.oauth2": pacote_oauth2,
            "google.oauth2.credentials": modulo_credentials,
        }

        with tempfile.TemporaryDirectory() as folder:
            client = Path(folder) / "oauth.json"
            token = Path(folder) / "token.json"
            client.write_text("{}", encoding="utf-8")
            token.write_text(json.dumps(token_info), encoding="utf-8")
            with (
                patch.dict("sys.modules", modulos_google),
                patch("nixal_integracao_gmail.CLIENT_FILE", client),
                patch("nixal_integracao_gmail.TOKEN_FILE", token),
            ):
                resultado = IntegracaoGmailNixOS()._credentials()

            self.assertIs(resultado, credenciais)
            classe_credentials.from_authorized_user_info.assert_called_once_with(
                token_info,
                scopes=escopos_esperados,
            )
            credenciais.refresh.assert_called_once()
            token_persistido = json.loads(token.read_text(encoding="utf-8"))
            self.assertEqual(token_persistido["scopes"], escopos_esperados)
            self.assertTrue(
                all(isinstance(escopo, str) for escopo in credenciais.scopes)
            )
            self.assertEqual(token.stat().st_mode & 0o777, 0o600)

    def test_lista_eventos_limita_janela_a_quatorze_dias(self):
        service = MagicMock()
        service.events.return_value.list.return_value.execute.return_value = {
            "items": [{
                "id": "event-1",
                "summary": "Reunião",
                "start": {"dateTime": "2026-10-10T14:00:00Z"},
                "end": {"dateTime": "2026-10-10T15:00:00Z"},
                "location": "Online",
                "htmlLink": "https://calendar.google.com/event",
            }]
        }
        with patch.object(IntegracaoGmailNixOS, "_service", return_value=service):
            result = IntegracaoGmailNixOS().listar_eventos(limite=500, dias=90)
        call = service.events.return_value.list.call_args.kwargs
        self.assertEqual(call["maxResults"], 50)
        self.assertIn("timeMin", call)
        self.assertIn("timeMax", call)
        self.assertEqual(result["dias"], 14)
        self.assertEqual(result["eventos"][0]["titulo"], "Reunião")
        self.assertTrue(result["somente_leitura"])

    def test_lista_contatos_somente_campos_autorizados(self):
        service = MagicMock()
        service.people.return_value.connections.return_value.list.return_value.execute.return_value = {
            "connections": [{
                "resourceName": "people/1",
                "names": [{"displayName": "Contato"}],
                "emailAddresses": [{"value": "contact@example.com"}],
                "phoneNumbers": [{"value": "+5511999999999"}],
            }]
        }
        with patch.object(IntegracaoGmailNixOS, "_service", return_value=service):
            result = IntegracaoGmailNixOS().listar_contatos(limite=500)
        call = service.people.return_value.connections.return_value.list.call_args.kwargs
        self.assertEqual(call["pageSize"], 100)
        self.assertEqual(call["personFields"], "names,emailAddresses,phoneNumbers")
        self.assertEqual(result["contatos"][0]["nome"], "Contato")
        self.assertTrue(result["somente_leitura"])

    def test_drive_retorna_metadados_sem_conteudo(self):
        service = MagicMock()
        service.files.return_value.list.return_value.execute.return_value = {
            "files": [{
                "id": "file-1", "name": "plano.txt", "mimeType": "text/plain",
                "modifiedTime": "2026-10-08T12:00:00Z",
                "webViewLink": "https://drive.google.com/file/d/file-1",
                "owners": [{"displayName": "Operador"}],
            }]
        }
        with patch.object(IntegracaoGmailNixOS, "_service", return_value=service):
            result = IntegracaoGmailNixOS().listar_arquivos_drive(limite=500)
        call = service.files.return_value.list.call_args.kwargs
        self.assertEqual(call["pageSize"], 100)
        self.assertIn("mimeType", call["fields"])
        self.assertNotIn("content", call["fields"].lower())
        self.assertTrue(result["metadados_apenas"])
        self.assertEqual(result["arquivos"][0]["nome"], "plano.txt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
