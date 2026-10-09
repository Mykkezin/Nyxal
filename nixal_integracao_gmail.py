#!/usr/bin/env python3
"""Google Workspace OAuth readonly bridge: Gmail, Calendar, Contacts, Drive.

OAuth client and tokens are local-only, outside the repository. This module
never sends, deletes, modifies, archives, or downloads Drive file contents.
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
CONFIG_DIR = Path(os.environ.get("NYXAL_CONFIG_DIR", str(Path.home() / ".config" / "nyxal"))).expanduser()
CLIENT_FILE = Path(os.environ.get("NYXAL_GOOGLE_CLIENT_FILE", str(CONFIG_DIR / "google-oauth-client.json"))).expanduser()
TOKEN_FILE = Path(os.environ.get("NYXAL_GMAIL_TOKEN_FILE", str(CONFIG_DIR / "google-workspace-token.json"))).expanduser()


class IntegracaoGmailNixOS:
    FONTE = "google_workspace_oauth"
    VERSAO = "1.1.0"
    SERVICES = {
        "gmail": ("gmail", "v1"),
        "calendar": ("calendar", "v3"),
        "people": ("people", "v1"),
        "drive": ("drive", "v3"),
    }

    def status(self) -> dict[str, Any]:
        dependencies = self._dependencies_available()
        token_exists = TOKEN_FILE.is_file()
        client_exists = CLIENT_FILE.is_file()
        granted_scopes: set[str] = set()
        if token_exists:
            try:
                token_info = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
                token_scopes = token_info.get("scopes", [])
                if isinstance(token_scopes, str):
                    token_scopes = token_scopes.split()
                if isinstance(token_scopes, list):
                    granted_scopes = {str(scope) for scope in token_scopes}
            except (OSError, json.JSONDecodeError):
                granted_scopes = set()
        missing_scopes = sorted(set(SCOPES) - granted_scopes) if granted_scopes else list(SCOPES)
        ready = dependencies and token_exists and client_exists and not missing_scopes
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "configurado" if ready else "configuracao_pendente",
            "somente_leitura": True,
            "dependencias_instaladas": dependencies,
            "arquivo_cliente_oauth_presente": client_exists,
            "token_oauth_presente": token_exists,
            "escopos_necessarios": SCOPES,
            "escopos_ausentes": missing_scopes,
            "servicos": {
                "gmail": "leitura de mensagens e snippets",
                "calendar": "próximos eventos por até 14 dias",
                "contacts": "nomes, e-mails e telefones",
                "drive": "metadados de arquivos, sem baixar conteúdo",
            },
            "pode_enviar_email": False,
            "pode_apagar_ou_alterar_email": False,
            "pode_alterar_calendario": False,
            "pode_modificar_contatos": False,
            "pode_modificar_ou_baixar_drive": False,
            "proximo_passo": None if ready else (
                "Instalar deploy/agent/requirements-gmail.txt, baixar credenciais OAuth Desktop do Google Cloud "
                "para " + str(CLIENT_FILE) + " e executar scripts/autorizar_gmail_nyxal.py. "
                "O fluxo solicita novo consentimento para os quatro escopos de leitura."
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

    def _credentials(self):
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2.credentials import Credentials
        except ImportError as exc:
            raise RuntimeError(
                "Dependências Google ausentes; instale deploy/agent/requirements-gmail.txt."
            ) from exc

        if not CLIENT_FILE.is_file():
            raise RuntimeError(f"Credenciais OAuth não encontradas em {CLIENT_FILE}.")
        if not TOKEN_FILE.is_file():
            raise RuntimeError("Google Workspace ainda não autorizado. Execute scripts/autorizar_gmail_nyxal.py.")

        try:
            token_info = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("O token Google não pode ser lido; refaça a autorização OAuth.") from exc
        token_scopes = token_info.get("scopes", [])
        if isinstance(token_scopes, str):
            token_scopes = token_scopes.split()
        granted_scopes = {str(scope) for scope in token_scopes} if isinstance(token_scopes, list) else set()
        if not set(SCOPES).issubset(granted_scopes):
            raise RuntimeError(
                "O token atual não contém todos os escopos Google Workspace requeridos. "
                "Execute novamente scripts/autorizar_gmail_nyxal.py e aceite o consentimento."
            )

        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
            TOKEN_FILE.chmod(0o600)
        if not credentials.valid:
            raise RuntimeError("Token Google expirado ou inválido; execute novamente o fluxo de autorização.")
        return credentials

    def _service(self, service_name: str):
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError("Dependência google-api-python-client ausente.") from exc
        if service_name not in self.SERVICES:
            raise ValueError("Serviço Google não permitido.")
        name, version = self.SERVICES[service_name]
        return build(name, version, credentials=self._credentials(), cache_discovery=False)

    def listar_mensagens(self, query: str = "is:unread newer_than:7d", limite: int = 10) -> dict[str, Any]:
        query = query.strip() or "is:unread newer_than:7d"
        limite = max(1, min(int(limite), 25))
        service = self._service("gmail")
        listing = service.users().messages().list(userId="me", q=query, maxResults=limite).execute()
        summaries = []
        for entry in listing.get("messages", []) or []:
            message_id = entry.get("id")
            if not message_id:
                continue
            item = service.users().messages().get(
                userId="me", id=message_id, format="metadata",
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
        message = self._service("gmail").users().messages().get(
            userId="me", id=message_id.strip(), format="full",
        ).execute()
        payload = message.get("payload", {})
        headers = {
            str(header.get("name", "")).lower(): str(header.get("value", ""))
            for header in payload.get("headers", [])
            if isinstance(header, dict)
        }
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
            "corpo_texto": self._plain_text(payload)[:20000],
        }

    def listar_eventos(self, limite: int = 20, dias: int = 14) -> dict[str, Any]:
        limite = max(1, min(int(limite), 50))
        dias = max(1, min(int(dias), 14))
        now = datetime.now(timezone.utc)
        service = self._service("calendar")
        raw = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat().replace("+00:00", "Z"),
            timeMax=(now + timedelta(days=dias)).isoformat().replace("+00:00", "Z"),
            maxResults=limite,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for item in raw.get("items", []) or []:
            start = item.get("start", {})
            end = item.get("end", {})
            events.append({
                "id": item.get("id"),
                "titulo": str(item.get("summary", "(sem título)"))[:300],
                "inicio": start.get("dateTime") or start.get("date"),
                "fim": end.get("dateTime") or end.get("date"),
                "status": item.get("status"),
                "link": item.get("htmlLink"),
                "local": str(item.get("location", ""))[:300] or None,
            })
        return {
            "sucesso": True, "estado": "eventos_listados", "origem": self.FONTE,
            "somente_leitura": True, "dias": dias, "quantidade": len(events), "eventos": events,
        }

    def listar_contatos(self, limite: int = 25) -> dict[str, Any]:
        limite = max(1, min(int(limite), 100))
        raw = self._service("people").people().connections().list(
            resourceName="people/me",
            pageSize=limite,
            personFields="names,emailAddresses,phoneNumbers",
        ).execute()
        contacts = []
        for item in raw.get("connections", []) or []:
            names = item.get("names", []) or []
            emails = item.get("emailAddresses", []) or []
            phones = item.get("phoneNumbers", []) or []
            contacts.append({
                "id": item.get("resourceName"),
                "nome": str(names[0].get("displayName", ""))[:300] if names else "",
                "emails": [str(x.get("value", ""))[:300] for x in emails[:5] if isinstance(x, dict)],
                "telefones": [str(x.get("value", ""))[:80] for x in phones[:5] if isinstance(x, dict)],
            })
        return {
            "sucesso": True, "estado": "contatos_listados", "origem": self.FONTE,
            "somente_leitura": True, "quantidade": len(contacts), "contatos": contacts,
        }

    def listar_arquivos_drive(self, limite: int = 25) -> dict[str, Any]:
        limite = max(1, min(int(limite), 100))
        raw = self._service("drive").files().list(
            q="trashed = false",
            pageSize=limite,
            orderBy="modifiedTime desc",
            fields="files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName,emailAddress))",
        ).execute()
        files = []
        for item in raw.get("files", []) or []:
            owners = item.get("owners", []) or []
            files.append({
                "id": item.get("id"),
                "nome": str(item.get("name", "(sem nome)"))[:300],
                "tipo": str(item.get("mimeType", ""))[:200],
                "modificado_em": item.get("modifiedTime"),
                "link": item.get("webViewLink"),
                "proprietario": str(owners[0].get("displayName", ""))[:200] if owners else None,
            })
        return {
            "sucesso": True, "estado": "arquivos_listados", "origem": self.FONTE,
            "somente_leitura": True, "metadados_apenas": True,
            "quantidade": len(files), "arquivos": files,
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
