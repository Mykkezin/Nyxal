#!/usr/bin/env python3
"""Integração Gmail via OAuth, inicialmente somente leitura.

Não envia, apaga, arquiva nem modifica mensagens. OAuth client e tokens ficam
fora do repositório em ~/.config/nyxal, com permissões restritas.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CONFIG_DIR = Path(os.environ.get("NYXAL_CONFIG_DIR", str(Path.home() / ".config" / "nyxal"))).expanduser()
CLIENT_FILE = Path(os.environ.get("NYXAL_GOOGLE_CLIENT_FILE", str(CONFIG_DIR / "google-oauth-client.json"))).expanduser()
TOKEN_FILE = Path(os.environ.get("NYXAL_GMAIL_TOKEN_FILE", str(CONFIG_DIR / "gmail-token.json"))).expanduser()


class IntegracaoGmailNixOS:
    FONTE = "gmail_api_oauth"
    VERSAO = "1.0.0"

    def status(self) -> dict[str, Any]:
        dependencies = self._dependencies_available()
        token_exists = TOKEN_FILE.is_file()
        client_exists = CLIENT_FILE.is_file()
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "configurado" if dependencies and token_exists and client_exists else "configuracao_pendente",
            "somente_leitura": True,
            "dependencias_instaladas": dependencies,
            "arquivo_cliente_oauth_presente": client_exists,
            "token_oauth_presente": token_exists,
            "escopos": SCOPES,
            "pode_enviar_email": False,
            "pode_apagar_ou_alterar_email": False,
            "proximo_passo": None if dependencies and token_exists and client_exists else (
                "Instalar deploy/agent/requirements-gmail.txt, baixar credenciais OAuth Desktop do Google Cloud "
                "para " + str(CLIENT_FILE) + " e executar scripts/autorizar_gmail_nyxal.py."
            ),
        }

    @staticmethod
    def _dependencies_available() -> bool:
        try:
            import googleapiclient.discovery  # noqa: F401
            import google.oauth2.credentials  # noqa: F401
            import google_auth_oauthlib.flow  # noqa: F401
            return True
        except ImportError:
            return False

    def _service(self):
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Dependências Gmail ausentes; instale deploy/agent/requirements-gmail.txt."
            ) from exc

        if not CLIENT_FILE.is_file():
            raise RuntimeError(f"Credenciais OAuth não encontradas em {CLIENT_FILE}.")
        if not TOKEN_FILE.is_file():
            raise RuntimeError("Gmail ainda não autorizado. Execute scripts/autorizar_gmail_nyxal.py.")

        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
            TOKEN_FILE.chmod(0o600)
        if not credentials.valid:
            raise RuntimeError("Token Gmail expirado ou inválido; execute novamente o fluxo de autorização.")
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def listar_mensagens(self, query: str = "is:unread newer_than:7d", limite: int = 10) -> dict[str, Any]:
        query = query.strip() or "is:unread newer_than:7d"
        limite = max(1, min(int(limite), 25))
        service = self._service()
        listing = service.users().messages().list(
            userId="me", q=query, maxResults=limite,
        ).execute()
        summaries = []
        for entry in listing.get("messages", []) or []:
            message_id = entry.get("id")
            if not message_id:
                continue
            item = service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            headers = {
                str(header.get("name", "")).lower(): str(header.get("value", ""))
                for header in item.get("payload", {}).get("headers", [])
                if isinstance(header, dict)
            }
            summaries.append({
                "id": message_id,
                "thread_id": item.get("threadId"),
                "assunto": headers.get("subject", "(sem assunto)")[:300],
                "remetente": headers.get("from", "")[:500],
                "data": headers.get("date", "")[:200],
                "trecho": str(item.get("snippet", ""))[:1000],
                "lidos": "UNREAD" not in item.get("labelIds", []),
            })
        return {
            "sucesso": True,
            "estado": "mensagens_listadas",
            "origem": self.FONTE,
            "somente_leitura": True,
            "consulta": query[:500],
            "quantidade": len(summaries),
            "mensagens": summaries,
        }

    def obter_mensagem(self, message_id: str) -> dict[str, Any]:
        if not isinstance(message_id, str) or not message_id.strip() or len(message_id) > 300:
            raise ValueError("ID de mensagem inválido.")
        message = self._service().users().messages().get(
            userId="me", id=message_id.strip(), format="full",
        ).execute()
        payload = message.get("payload", {})
        headers = {
            str(header.get("name", "")).lower(): str(header.get("value", ""))
            for header in payload.get("headers", [])
            if isinstance(header, dict)
        }
        body = self._plain_text(payload)
        return {
            "sucesso": True,
            "estado": "mensagem_lida",
            "origem": self.FONTE,
            "somente_leitura": True,
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "assunto": headers.get("subject", "(sem assunto)")[:300],
            "remetente": headers.get("from", "")[:500],
            "data": headers.get("date", "")[:200],
            "corpo_texto": body[:20000],
        }

    @classmethod
    def _plain_text(cls, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return ""
        mime = str(payload.get("mimeType", ""))
        body = payload.get("body", {})
        if mime == "text/plain" and isinstance(body, dict) and body.get("data"):
            try:
                return base64.urlsafe_b64decode(body["data"] + "==").decode("utf-8", errors="replace")
            except Exception:
                return ""
        output = []
        for part in payload.get("parts", []) or []:
            if isinstance(part, dict):
                value = cls._plain_text(part)
                if value:
                    output.append(value)
        return "\n".join(output)


__all__ = ["IntegracaoGmailNixOS", "SCOPES"]
