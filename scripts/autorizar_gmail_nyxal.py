#!/usr/bin/env python3
"""Autoriza acesso Gmail readonly por OAuth desktop, de forma interativa."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from nixal_integracao_gmail import CLIENT_FILE, SCOPES, TOKEN_FILE


def main() -> int:
    if not CLIENT_FILE.is_file():
        print(f"Credenciais OAuth não encontradas: {CLIENT_FILE}", file=sys.stderr)
        print("Baixe OAuth Client ID do tipo Desktop App no Google Cloud Console.", file=sys.stderr)
        return 2
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Dependência ausente. Instale deploy/agent/requirements-gmail.txt.", file=sys.stderr)
        return 2

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    credentials = flow.run_local_server(port=0, open_browser=True)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    try:
        CLIENT_FILE.chmod(0o600)
    except OSError:
        pass
    print(f"Gmail autorizado em modo somente leitura. Token guardado em {TOKEN_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
