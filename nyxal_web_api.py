#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import compare_digest

from nixal_executor_ordens import ExecutorOrdensNixal


BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("NYXAL_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("NYXAL_API_PORT", "8010"))
API_TOKEN = os.environ.get("NYXAL_API_TOKEN", "")
CORS_ORIGIN = os.environ.get("NYXAL_API_CORS_ORIGIN", "*")
EXECUTOR = ExecutorOrdensNixal()
PIPER_BIN = Path(sys.executable).resolve().parent / "piper"
TTS_MODEL = Path(
    os.environ.get(
        "NYXAL_TTS_MODEL",
        str(BASE_DIR / "voices/dii_pt-BR/dii_pt-BR.onnx"),
    )
)


def json_bytes(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def format_chat_response(resultado: dict) -> str:
    if not resultado.get("sucesso"):
        return str(
            resultado.get(
                "motivo",
                "Não foi possível concluir a ordem.",
            )
        )

    execucao = (
        resultado.get("valor", {})
        .get("execucao", {})
    )
    pacote = execucao.get("valor", {})
    capacidade = pacote.get("capacidade")
    valor = pacote.get("resultado")

    if capacidade == "obter_hora" and isinstance(valor, dict):
        hora = valor.get("hora")
        minuto = valor.get("minuto")
        segundo = valor.get("segundo")

        if all(isinstance(item, int) for item in (hora, minuto, segundo)):
            return (
                f"Agora são {hora:02d}:{minuto:02d}:{segundo:02d}."
            )

    if capacidade == "listar_arquivos" and isinstance(valor, list):
        quantidade = len(valor)
        if quantidade == 0:
            return "A pasta atual não contém arquivos listados."
        return f"Encontrei {quantidade} arquivos na pasta atual."

    if isinstance(valor, str):
        return valor

    return "Ordem executada com sucesso pela Nyxal."


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
            "GET, POST, OPTIONS",
        )
        self.end_headers()

        self.wfile.write(body)

    def _send_bytes(
        self,
        status_code: int,
        body: bytes,
        content_type: str,
    ) -> None:
        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            content_type,
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
            "GET, POST, OPTIONS",
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
            "GET, POST, OPTIONS",
        )
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/tts":
            try:
                content_length = int(
                    self.headers.get("Content-Length", "0")
                )
            except ValueError:
                self._send_json(
                    400,
                    {
                        "estado": "entrada_invalida",
                        "motivo": "Content-Length inválido.",
                    },
                )
                return

            if content_length <= 0 or content_length > 16 * 1024:
                self._send_json(
                    400 if content_length <= 0 else 413,
                    {
                        "estado": (
                            "entrada_invalida"
                            if content_length <= 0
                            else "entrada_muito_grande"
                        ),
                        "motivo": (
                            "O corpo da requisição é obrigatório."
                            if content_length <= 0
                            else "O corpo da requisição excede 16 KiB."
                        ),
                    },
                )
                return

            try:
                payload = json.loads(
                    self.rfile.read(content_length).decode("utf-8")
                )
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                self._send_json(
                    400,
                    {
                        "estado": "entrada_invalida",
                        "motivo": "O corpo precisa ser um JSON UTF-8 válido.",
                    },
                )
                return

            texto = (
                payload.get("texto")
                if isinstance(payload, dict)
                else None
            )

            if not isinstance(texto, str) or not texto.strip():
                self._send_json(
                    400,
                    {
                        "estado": "entrada_invalida",
                        "motivo": "O campo 'texto' precisa ser um texto não vazio.",
                    },
                )
                return

            if not PIPER_BIN.exists() or not TTS_MODEL.exists():
                self._send_json(
                    503,
                    {
                        "estado": "tts_nao_configurado",
                        "motivo": "Piper ou o modelo de voz da Nyxal não foi encontrado.",
                    },
                )
                return

            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".wav",
                    dir="/tmp",
                ) as arquivo_audio:
                    processo = subprocess.run(
                        [
                            str(PIPER_BIN),
                            "--model",
                            str(TTS_MODEL),
                            "--output_file",
                            arquivo_audio.name,
                        ],
                        input=texto.strip() + "\n",
                        text=True,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )

                    if processo.returncode != 0:
                        self._send_json(
                            500,
                            {
                                "estado": "erro_ao_gerar_audio",
                                "motivo": (
                                    processo.stderr.strip()
                                    or "O Piper não conseguiu gerar o áudio."
                                ),
                            },
                        )
                        return

                    arquivo_audio.seek(0)
                    audio = arquivo_audio.read()

                self._send_bytes(
                    200,
                    audio,
                    "audio/wav",
                )
            except subprocess.TimeoutExpired:
                self._send_json(
                    504,
                    {
                        "estado": "tts_timeout",
                        "motivo": "A geração do áudio excedeu 30 segundos.",
                    },
                )
            except OSError as erro:
                self._send_json(
                    500,
                    {
                        "estado": "erro_ao_gerar_audio",
                        "motivo": str(erro),
                    },
                )
            return

        if self.path != "/api/chat":
        if self.path != "/api/chat":
            self._send_json(
                404,
                {
                    "estado": "rota_nao_encontrada",
                },
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )
        except ValueError:
            self._send_json(
                400,
                {
                    "estado": "entrada_invalida",
                    "motivo": "Content-Length inválido.",
                },
            )
            return

        if content_length <= 0:
            self._send_json(
                400,
                {
                    "estado": "entrada_invalida",
                    "motivo": "O corpo da requisição é obrigatório.",
                },
            )
            return

        if content_length > 64 * 1024:
            self._send_json(
                413,
                {
                    "estado": "entrada_muito_grande",
                    "motivo": "O corpo da requisição excede 64 KiB.",
                },
            )
            return

        try:
            payload = json.loads(
                self.rfile.read(content_length).decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            self._send_json(
                400,
                {
                    "estado": "entrada_invalida",
                    "motivo": "O corpo precisa ser um JSON UTF-8 válido.",
                },
            )
            return

        if not isinstance(payload, dict):
            self._send_json(
                400,
                {
                    "estado": "entrada_invalida",
                    "motivo": "O corpo precisa ser um objeto JSON.",
                },
            )
            return

        mensagem = payload.get("mensagem")

        if not isinstance(mensagem, str) or not mensagem.strip():
            self._send_json(
                400,
                {
                    "estado": "entrada_invalida",
                    "motivo": "O campo 'mensagem' precisa ser um texto não vazio.",
                },
            )
            return

        try:
            resultado = EXECUTOR.atender(mensagem)
        except Exception as erro:
            self._send_json(
                500,
                {
                    "estado": "erro_ao_atender_ordem",
                    "motivo": str(erro),
                },
            )
            return

        resposta = dict(resultado)
        resposta["resposta"] = format_chat_response(resultado)

        self._send_json(
            200 if resultado.get("sucesso") else 422,
            resposta,
        )

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
    print(
        "[Nyxal-API] endpoint de chat: "
        "POST /api/chat"
    )
    print(
        "[Nyxal-API] endpoint de voz: "
        "POST /api/tts"
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
