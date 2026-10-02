#!/usr/bin/env python3

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import compare_digest


BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("NYXAL_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("NYXAL_API_PORT", "8010"))
API_TOKEN = os.environ.get("NYXAL_API_TOKEN", "")
CORS_ORIGIN = os.environ.get("NYXAL_API_CORS_ORIGIN", "*")


def json_bytes(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def read_status() -> dict:
    estado_path = BASE_DIR / "estado_nixal.json"

    if not estado_path.exists():
        return {
            "estado": "arquivo_de_estado_nao_encontrado",
            "identidade": {
                "nome": "Nixal",
            },
        }

    try:
        estado = json.loads(
            estado_path.read_text(
                encoding="utf-8",
            )
        )

        if not isinstance(estado, dict):
            raise ValueError("estado da Nyxal não é um objeto JSON")

        return estado

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as erro:
        return {
            "estado": "erro_ao_ler_estado",
            "erro": str(erro),
        }


class NyxalAPIHandler(BaseHTTPRequestHandler):
    server_version = "NyxalAPI/1.0"

    def _send_json(
        self,
        status_code: int,
        payload: dict,
    ) -> None:
        body = json_bytes(payload)

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.send_header(
            "Access-Control-Allow-Origin",
            CORS_ORIGIN,
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS",
        )
        self.end_headers()

        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not API_TOKEN:
            self._send_json(
                503,
                {
                    "estado": "api_nao_configurada",
                    "erro": "NYXAL_API_TOKEN não configurado",
                },
            )
            return False

        authorization = self.headers.get(
            "Authorization",
            "",
        )

        if not authorization.startswith("Bearer "):
            self._send_json(
                401,
                {
                    "estado": "nao_autorizado",
                },
            )
            return False

        token = authorization.removeprefix("Bearer ").strip()

        if not compare_digest(token, API_TOKEN):
            self._send_json(
                403,
                {
                    "estado": "acesso_negado",
                },
            )
            return False

        return True

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header(
            "Access-Control-Allow-Origin",
            CORS_ORIGIN,
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS",
        )
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "servico": "nyxal-api",
                    "estado": "ativo",
                },
            )
            return

        if self.path == "/api/public/status":
            estado = read_status()

            identidade = estado.get("identidade", {})
            presenca = estado.get("presenca", {})
            estado_operacional = estado.get("estado", {})

            self._send_json(
                200,
                {
                    "identidade": {
                        "nome": identidade.get("nome"),
                        "versao": identidade.get("versao"),
                    },
                    "presenca": {
                        "ativa": presenca.get("ativa"),
                        "ultimo_ciclo": presenca.get("ultimo_ciclo"),
                        "ciclos": presenca.get("ciclos"),
                    },
                    "estado": {
                        "modo": estado_operacional.get("modo"),
                        "status": estado_operacional.get("status"),
                    },
                },
            )
            return

        if self.path == "/api/status":
            if not self._authorized():
                return

            self._send_json(
                200,
                read_status(),
            )
            return

        self._send_json(
            404,
            {
                "estado": "rota_nao_encontrada",
            },
        )

    def log_message(
        self,
        format_string: str,
        *args,
    ) -> None:
        print(
            "[Nyxal-API]",
            format_string % args,
        )


def main() -> None:
    server = ThreadingHTTPServer(
        (HOST, PORT),
        NyxalAPIHandler,
    )

    print(
        f"[Nyxal-API] escutando em "
        f"http://{HOST}:{PORT}"
    )
    print(
        "[Nyxal-API] endpoint protegido: "
        "GET /api/status"
    )
    print(
        "[Nyxal-API] endpoint publico: "
        "GET /api/public/status"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("[Nyxal-API] encerrando...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
