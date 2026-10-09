#!/usr/bin/env python3
"""Conectores Google pessoais da Nyxal: Gmail, Calendar, Contacts e Drive metadata.

Todos os escopos são somente leitura. Credenciais ficam em ~/.config/nyxal,
fora do repositório; nenhum endpoint desta integração modifica contas ou conteúdo.
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
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]
CONFIG_DIR = Path(os.environ.get("NYXAL_CONFIG_DIR", str(Path.home() / ".config" / "nyxal"))).expanduser()
CLIENT_FILE = Path(os.environ.get("NYXAL_GOOGLE_CLIENT_FILE", str(CONFIG_DIR / "google-oauth-client.json"))).expanduser()
TOKEN_FILE = Path(os.environ.get("NYXAL_GMAIL_TOKEN_FILE", str(CONFIG_DIR / "gmail-token.json"))).expanduser()


class IntegracaoGmailNixOS:
    FONTE = "google_workspace_oauth_readonly"
    VERSAO = "1.1.0"

    def status(self) -> dict[str, Any]:
        dependencies = self._dependencies_available()
        token_exists = TOKEN_FILE.is_file()
        client_exists = CLIENT_FILE.is_file()
        token_scopes: set[str] = set()
        token_error = None
        if token_exists:
            try:
                raw = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
                scopes = raw.get("scopes", []) if isinstance(raw, dict) else []
                if isinstance(scopes, str):
                    token_scopes = set(scopes.split())
                elif isinstance(scopes, list):
                    token_scopes = {value for value in scopes if isinstance(value, str)}
            except (OSError, json.JSONDecodeError):
                token_error = "token_json_invalido"
        missing_scopes = [scope for scope in SCOPES if scope not in token_scopes]
        complete = dependencies and token_exists and client_exists and not missing_scopes and not token_error
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "configurado" if complete else "configuracao_pendente",
            "somente_leitura": True,
            "dependencias_instaladas": dependencies,
            "arquivo_cliente_oauth_presente": client_exists,
            "token_oauth_presente": token_exists,
            "escopos": SCOPES,
            "escopos_autorizados": sorted(token_scopes),
            "escopos_ausentes": missing_scopes,
            "erro_token": token_error,
            "servicos_disponiveis": {
                "gmail": SCOPES[0] not in missing_scopes,
                "agenda": SCOPES[1] not in missing_scopes,
                "contatos": SCOPES[2] not in missing_scopes,
                "drive_metadados": SCOPES[3] not in missing_scopes,
            },
            "pode_enviar_email": False,
            "pode_apagar_ou_alterar_email": False,
            "pode_editar_agenda": False,
            "pode_editar_contatos": False,
            "pode_ler_conteudo_arquivos_drive": False,
            "proximo_passo": None if complete else (
                "Instale deploy/agent/requirements-gmail.txt, configure OAuth Desktop no Google Cloud "
                "e execute scripts/autorizar_gmail_nyxal.py para consentir os quatro escopos somente leitura."
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

        credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE))
        current_scopes = set(credentials.scopes or [])
        missing = [scope for scope in SCOPES if scope not in current_scopes]
        if missing:
            raise RuntimeError(
                "Autorização Google incompleta. Execute novamente scripts/autorizar_gmail_nyxal.py "
                "e aceite os escopos Gmail, Agenda, Contatos e metadados do Drive."
            )
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
            TOKEN_FILE.chmod(0o600)
        if not credentials.valid:
            raise RuntimeError("Token Google expirado ou inválido; execute novamente o fluxo OAuth.")
        return credentials

    def _service(self, service_name: str = "gmail", version: str = "v1"):
        return self._google_service(service_name, version)

    def _google_service(self, service_name: str, version: str):
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Dependências Google ausentes; instale deploy/agent/requirements-gmail.txt."
            ) from exc
        return build(service_name, version, credentials=self._credentials(), cache_discovery=False)

    def listar_mensagens(self, query: str = "is:unread newer_than:7d", limite: int = 10) -> dict[str, Any]:
        query = (query.strip() if isinstance(query, str) else "") or "is:unread newer_than:7d"
        query = query[:500]
        limite = max(1, min(int(limite), 25))
        service = self._service()
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
            "sucesso": True, "estado": "mensagens_listadas", "origem": self.FONTE,
            "somente_leitura": True, "consulta": query, "quantidade": len(summaries),
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
        return {
            "sucesso": True, "estado": "mensagem_lida", "origem": self.FONTE,
            "somente_leitura": True, "id": message.get("id"), "thread_id": message.get("threadId"),
            "assunto": headers.get("subject", "(sem assunto)")[:300],
            "remetente": headers.get("from", "")[:500],
            "data": headers.get("date", "")[:200],
            "corpo_texto": self._plain_text(payload)[:20000],
        }

    def listar_eventos(self, limite: int = 20, dias: int = 7) -> dict[str, Any]:
        limite = max(1, min(int(limite), 50))
        dias = max(1, min(int(dias), 14))
        service = self._service("calendar", "v3")
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=dias)
        response = service.events().list(
            calendarId="primary",
            timeMin=start.isoformat().replace("+00:00", "Z"),
            timeMax=end.isoformat().replace("+00:00", "Z"),
            maxResults=limite,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for item in response.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            events.append({
                "id": str(item.get("id", ""))[:300],
                "titulo": str(item.get("summary", "(sem título)"))[:300],
                "inicio": self._date_value(item.get("start")),
                "fim": self._date_value(item.get("end")),
                "local": str(item.get("location", ""))[:300],
                "link": str(item.get("htmlLink", ""))[:1000],
            })
        return {
            "sucesso": True, "estado": "eventos_listados", "origem": self.FONTE,
            "somente_leitura": True, "dias": dias, "quantidade": len(events), "eventos": events,
        }

    def listar_contatos(self, limite: int = 50) -> dict[str, Any]:
        limite = max(1, min(int(limite), 100))
        service = self._service("people", "v1")
        response = service.people().connections().list(
            resourceName="people/me",
            pageSize=limite,
            personFields="names,emailAddresses,phoneNumbers",
        ).execute()
        contacts = []
        for item in response.get("connections", []) or []:
            if not isinstance(item, dict):
                continue
            names = item.get("names", []) or []
            emails = item.get("emailAddresses", []) or []
            phones = item.get("phoneNumbers", []) or []
            contacts.append({
                "id": str(item.get("resourceName", ""))[:300],
                "nome": str(names[0].get("displayName", ""))[:300] if names and isinstance(names[0], dict) else "",
                "emails": [str(x.get("value", ""))[:300] for x in emails[:5] if isinstance(x, dict)],
                "telefones": [str(x.get("value", ""))[:100] for x in phones[:5] if isinstance(x, dict)],
            })
        return {
            "sucesso": True, "estado": "contatos_listados", "origem": self.FONTE,
            "somente_leitura": True, "quantidade": len(contacts), "contatos": contacts,
        }

    def listar_arquivos_drive(self, limite: int = 50) -> dict[str, Any]:
        limite = max(1, min(int(limite), 100))
        service = self._service("drive", "v3")
        response = service.files().list(
            q="trashed = false",
            pageSize=limite,
            orderBy="modifiedTime desc",
            fields="files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName,emailAddress))",
        ).execute()
        files = []
        for item in response.get("files", []) or []:
            if not isinstance(item, dict):
                continue
            owners = item.get("owners", []) or []
            files.append({
                "id": str(item.get("id", ""))[:300],
                "nome": str(item.get("name", "(sem nome)"))[:500],
                "tipo": str(item.get("mimeType", ""))[:200],
                "modificado_em": str(item.get("modifiedTime", ""))[:100],
                "link": str(item.get("webViewLink", ""))[:1000],
                "proprietario": str(owners[0].get("displayName", ""))[:200] if owners and isinstance(owners[0], dict) else "",
            })
        return {
            "sucesso": True, "estado": "arquivos_listados", "origem": self.FONTE,
            "somente_leitura": True, "metadados_apenas": True,
            "quantidade": len(files), "arquivos": files,
        }

    @staticmethod
    def _date_value(value: Any) -> str:
        if not isinstance(value, dict):
            return ""
        return str(value.get("dateTime") or value.get("date") or "")[:100]

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
