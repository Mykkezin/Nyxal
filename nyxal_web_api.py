#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import compare_digest

from nixal_nucleo_conversacional import (
    NucleoConversacionalNixal,
)
from nixal_transporte_conversacional import (
    TransporteConversacionalNixal,
)
from nixal_integracao_sessao_transporte import (
    IntegracaoSessaoTransporteNixal,
)
from nixal_habitat import HabitatNixOS
from nixal_persistencia_operacional import PersistenciaOperacionalNixOS
from nixal_delta import RegistroDeltaNixOS
from nixal_recursos_habitat import RecursosHabitatNixOS
from nixal_presenca_maquina import PresencaMaquinaNixOS
from nixal_descoberta_continua_ae5 import DescobertaContinuaGovernadaAE5
from nixal_coletor_dataset_dual_ae5 import ColetorDatasetDualAE5


BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("NYXAL_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("NYXAL_API_PORT", "8010"))
API_TOKEN = os.environ.get("NYXAL_API_TOKEN", "")
CORS_ORIGIN = os.environ.get("NYXAL_API_CORS_ORIGIN", "*")
NUCLEO_CONVERSACIONAL = NucleoConversacionalNixal()
INTEGRACAO_CONVERSACIONAL = IntegracaoSessaoTransporteNixal(
    transporte=TransporteConversacionalNixal(),
)
HABITAT_NYXOS = HabitatNixOS()
PERSISTENCIA_OPERACIONAL = PersistenciaOperacionalNixOS(
    BASE_DIR / "estado_nyxos_operacional.json"
)
DELTA_NYXOS = RegistroDeltaNixOS(
    BASE_DIR / "eventos_delta_nyxos.json"
)
RECURSOS_HABITAT = RecursosHabitatNixOS(BASE_DIR)
PRESENCA_MAQUINA = PresencaMaquinaNixOS(
    arquivo=BASE_DIR / "presenca_maquina_nyxos.json"
)
DESCOBERTA_CONTINUA_AE5 = DescobertaContinuaGovernadaAE5(
    repositorio=BASE_DIR,
    habilitada=False,
)
COLETOR_DATASET_DUAL_AE5 = ColetorDatasetDualAE5(
    repositorio=BASE_DIR,
    habilitada=False,
)
PIPER_BIN = Path(sys.executable).parent / "piper"
KOKORO_VOICE = os.environ.get("NYXAL_KOKORO_VOICE", "pf_dora")

try:
    KOKORO_SPEED = min(
        1.15,
        max(
            0.90,
            float(
                os.environ.get(
                    "NYXAL_KOKORO_SPEED",
                    "1.03",
                )
            ),
        ),
    )
except ValueError:
    KOKORO_SPEED = 1.03

WHISPER_MODEL_NAME = os.environ.get(
    "NYXAL_WHISPER_MODEL",
    "base",
)
WHISPER_MODEL = None
KOKORO_PIPELINE = None
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


def get_whisper_model():
    global WHISPER_MODEL

    if WHISPER_MODEL is None:
        from faster_whisper import WhisperModel

        WHISPER_MODEL = WhisperModel(
            WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
        )

    return WHISPER_MODEL


def transcribe_audio(audio_path: str) -> str:
    model = get_whisper_model()

    segments, _ = model.transcribe(
        audio_path,
        language="pt",
        vad_filter=True,
        condition_on_previous_text=False,
        temperature=0.0,
    )

    texto = " ".join(
        segmento.text.strip()
        for segmento in segments
        if segmento.text.strip()
    ).strip()

    return normalizar_texto_stt(texto)


def texto_para_fala(texto: str) -> str:
    """
    Converte os nomes escritos da Nyxal para a pronúncia desejada
    no TTS, sem alterar o texto visual retornado pela API.
    """
    substituicoes = {
        "Myqueyas": "Mayqueas",
        "Myke": "Mayque",
        "MYKE": "MAYQUE",
        "Nyxal": "Niquischáu",
        "NYXAL": "NIQUISCHÁU",
    }

    resultado = texto
    for escrito, falado in substituicoes.items():
        resultado = resultado.replace(escrito, falado)

    return resultado


def normalizar_texto_stt(texto: str) -> str:
    """
    Converte aproximações fonéticas do reconhecimento de voz
    para a grafia oficial usada pela Nyxal.
    """
    import re

    resultado = texto

    substituicoes = (
        (
            r"\bsenhora\s+myke\b",
            "senhor Myke",
        ),
        (
            r"\bsenhora\s+(?:myque|mike|mayque|maique|maike|myk)\b",
            "senhor Myke",
        ),
        (
            r"\b(?:myque|myke|mike|mayque|maique|maike|myk)\b",
            "Myke",
        ),
        (
            r"\b(?:nixal|aniksao|anixao|niquischau|niquichau|niquis hau|niquischáu)\b",
            "Nyxal",
        ),
        (
            r"\beu\s+sou\s+(?:a\s+)?nyxal\b",
            "eu sou a Nyxal",
        ),
        (
            r"\be\s+eu\s+sou\s+(?:a\s+)?nyxal\b",
            "e eu sou a Nyxal",
        ),
    )

    for padrao, substituto in substituicoes:
        resultado = re.sub(
            padrao,
            substituto,
            resultado,
            flags=re.IGNORECASE,
        )

    return resultado


def suavizar_audio_kokoro(
    chunks,
    sample_rate: int = 24000,
):
    """
    Junta segmentos do Kokoro com micro-fades/crossfade para reduzir
    pequenos cliques ou cortes perceptíveis entre trechos.
    """
    import numpy as np

    segmentos = [
        np.asarray(chunk, dtype=np.float32).reshape(-1)
        for chunk in chunks
        if np.asarray(chunk).size
    ]

    if not segmentos:
        raise RuntimeError(
            "O Kokoro não gerou nenhum segmento de áudio."
        )

    if len(segmentos) == 1:
        audio = segmentos[0].copy()
    else:
        audio = segmentos[0].copy()

        for segmento in segmentos[1:]:
            sobreposicao = min(
                int(sample_rate * 0.008),
                len(audio),
                len(segmento),
            )

            if sobreposicao <= 1:
                audio = np.concatenate(
                    (audio, segmento)
                )
                continue

            rampa = np.linspace(
                0.0,
                1.0,
                sobreposicao,
                dtype=np.float32,
            )

            trecho_final = audio[-sobreposicao:]
            trecho_inicial = segmento[:sobreposicao]

            audio[-sobreposicao:] = (
                trecho_final * (1.0 - rampa)
                + trecho_inicial * rampa
            )

            audio = np.concatenate(
                (audio, segmento[sobreposicao:])
            )

    fade = min(
        int(sample_rate * 0.005),
        len(audio) // 2,
    )

    if fade > 1:
        rampa_entrada = np.linspace(
            0.0,
            1.0,
            fade,
            dtype=np.float32,
        )
        rampa_saida = np.linspace(
            1.0,
            0.0,
            fade,
            dtype=np.float32,
        )

        audio[:fade] *= rampa_entrada
        audio[-fade:] *= rampa_saida

    pico = float(np.max(np.abs(audio)))

    if pico > 0.98:
        audio = audio * (0.98 / pico)

    return audio


def generate_kokoro_audio(texto: str) -> bytes:
    global KOKORO_PIPELINE

    if KOKORO_PIPELINE is None:
        from kokoro import KPipeline

        KOKORO_PIPELINE = KPipeline(
            lang_code="p",
        )

    import numpy as np
    import soundfile as sf

    chunks = []

    for _, _, audio in KOKORO_PIPELINE(
        texto_para_fala(texto),
        voice=KOKORO_VOICE,
        speed=KOKORO_SPEED,
    ):
        chunks.append(audio)

    audio = suavizar_audio_kokoro(
        chunks
    )

    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        dir="/tmp",
    ) as arquivo_audio:
        sf.write(
            arquivo_audio.name,
            audio,
            24000,
        )
        arquivo_audio.seek(0)
        return arquivo_audio.read()

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

    # A execução da capacidade pode encapsular o valor em outro
    # objeto de resultado. Desembrulhamos somente esse nível.
    if (
        isinstance(valor, dict)
        and "resultado" in valor
        and valor.get("capacidade") == capacidade
    ):
        valor = valor.get("resultado")

    if capacidade == "obter_hora" and isinstance(valor, dict):
        hora = valor.get("hora")
        minuto = valor.get("minuto")
        segundo = valor.get("segundo")

        if all(isinstance(item, int) for item in (hora, minuto, segundo)):
            periodo = (
                "da madrugada"
                if hora < 6
                else "da manhã"
                if hora < 12
                else "da tarde"
                if hora < 18
                else "da noite"
            )
            return (
                f"Agora são {hora:02d}:{minuto:02d}:{segundo:02d}, "
                f"{periodo}, senhor Myke."
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
        if self.path == "/api/stt":
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
                        "motivo": "O áudio é obrigatório.",
                    },
                )
                return

            if content_length > 15 * 1024 * 1024:
                self._send_json(
                    413,
                    {
                        "estado": "audio_muito_grande",
                        "motivo": "O áudio excede 15 MiB.",
                    },
                )
                return

            audio_data = self.rfile.read(content_length)
            content_type = (
                self.headers.get(
                    "Content-Type",
                    "application/octet-stream",
                )
                .split(";")[0]
                .strip()
                .lower()
            )

            extensoes = {
                "audio/webm": ".webm",
                "audio/ogg": ".ogg",
                "audio/wav": ".wav",
                "audio/x-wav": ".wav",
                "audio/mpeg": ".mp3",
                "audio/mp4": ".mp4",
                "audio/aac": ".aac",
            }
            suffix = extensoes.get(content_type, ".audio")

            try:
                with tempfile.NamedTemporaryFile(
                    suffix=suffix,
                    dir="/tmp",
                ) as arquivo_audio:
                    arquivo_audio.write(audio_data)
                    arquivo_audio.flush()

                    texto = transcribe_audio(
                        arquivo_audio.name
                    )

                self._send_json(
                    200,
                    {
                        "sucesso": True,
                        "estado": (
                            "transcricao_concluida"
                            if texto
                            else "audio_sem_fala"
                        ),
                        "texto": texto,
                        "modelo": WHISPER_MODEL_NAME,
                    },
                )
            except Exception as erro:
                self._send_json(
                    500,
                    {
                        "estado": "erro_ao_transcrever",
                        "motivo": str(erro),
                    },
                )
            return

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

            try:
                audio = generate_kokoro_audio(texto)

                self._send_bytes(
                    200,
                    audio,
                    "audio/wav",
                )
            except Exception as kokoro_erro:
                print(
                    "[Nyxal-API] Kokoro falhou; usando Piper:",
                    kokoro_erro,
                )

                if not PIPER_BIN.exists() or not TTS_MODEL.exists():
                    self._send_json(
                        503,
                        {
                            "estado": "tts_nao_configurado",
                            "motivo": "Kokoro e Piper não estão disponíveis.",
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
        sessao_id = payload.get("sessao")

        if not isinstance(mensagem, str) or not mensagem.strip():
            self._send_json(
                400,
                {
                    "estado": "entrada_invalida",
                    "motivo": "O campo 'mensagem' precisa ser um texto não vazio.",
                },
            )
            return

        if sessao_id is not None and (
            not isinstance(sessao_id, str)
            or not sessao_id.strip()
        ):
            self._send_json(
                400,
                {
                    "estado": "entrada_invalida",
                    "motivo": "O campo 'sessao' precisa ser uma string não vazia.",
                },
            )
            return

        try:
            resultado = (
                INTEGRACAO_CONVERSACIONAL.processar_mensagem(
                    texto=mensagem,
                    nucleo=NUCLEO_CONVERSACIONAL,
                    sessao_id=sessao_id,
                )
            )
        except Exception as erro:
            self._send_json(
                500,
                {
                    "estado": "erro_ao_processar_conversa",
                    "motivo": str(erro),
                },
            )
            return

        transporte = (
            resultado.get("valor", {})
            if isinstance(resultado.get("valor"), dict)
            else {}
        ).get("transporte", {})

        resposta_estruturada = (
            transporte.get("resposta")
            if isinstance(transporte, dict)
            else None
        )

        resposta_textual = (
            resposta_estruturada.get("resposta")
            if isinstance(resposta_estruturada, dict)
            else None
        )

        resposta = dict(resultado)
        resposta["resposta"] = (
            resposta_textual
            if isinstance(resposta_textual, str)
            else (
                resultado.get("erro")
                or "A Nyxal não conseguiu processar a mensagem."
            )
        )

        resposta["sessao"] = resultado.get("sessao")

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

            try:
                habitat = HABITAT_NYXOS.snapshot()
            except Exception as erro:
                habitat = {
                    "sucesso": False,
                    "estado": "habitat_indisponivel",
                    "origem": HABITAT_NYXOS.FONTE,
                    "versao": HABITAT_NYXOS.VERSAO,
                    "motivo": str(erro),
                }

            identidade = estado.get("identidade", {})
            presenca = estado.get("presenca", {})
            estado_operacional = estado.get("estado", {})

            try:
                persistencia_operacional = PERSISTENCIA_OPERACIONAL.contexto()
            except Exception as erro:
                persistencia_operacional = {
                    "sucesso": False,
                    "estado": "persistencia_operacional_indisponivel",
                    "origem": PERSISTENCIA_OPERACIONAL.FONTE,
                    "versao": PERSISTENCIA_OPERACIONAL.VERSAO,
                    "motivo": str(erro),
                }

            try:
                delta = DELTA_NYXOS.contexto()
            except Exception as erro:
                delta = {
                    "sucesso": False,
                    "estado": "delta_indisponivel",
                    "origem": DELTA_NYXOS.FONTE,
                    "versao": DELTA_NYXOS.VERSAO,
                    "motivo": str(erro),
                }

            try:
                recursos_habitat = RECURSOS_HABITAT.snapshot()
            except Exception as erro:
                recursos_habitat = {
                    "sucesso": False,
                    "estado": "recursos_habitat_indisponiveis",
                    "origem": RECURSOS_HABITAT.FONTE,
                    "versao": RECURSOS_HABITAT.VERSAO,
                    "motivo": str(erro),
                }

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
                    "presenca_maquina": PRESENCA_MAQUINA.contexto(),
                    "estado": {
                        "modo": estado_operacional.get("modo"),
                        "status": estado_operacional.get("status"),
                    },
                    "habitat": habitat,
                    "persistencia_operacional": persistencia_operacional,
                    "delta": delta,
                    "recursos_habitat": recursos_habitat,
                    "descoberta_continua_ae5": {
                        "versao": DESCOBERTA_CONTINUA_AE5.VERSAO,
                        "habilitada": False,
                        "linhas_economicas_ativas": DESCOBERTA_CONTINUA_AE5.contexto().get(
                            "linhas_economicas_ativas",
                            0,
                        ),
                        "linhas_maduras": DESCOBERTA_CONTINUA_AE5.contexto().get(
                            "linhas_maduras",
                            0,
                        ),
                    },
                    "datasets_ae5": {
                        "versao": COLETOR_DATASET_DUAL_AE5.VERSAO,
                        "qwen_registros": COLETOR_DATASET_DUAL_AE5.contexto()["datasets"]["qwen"]["registros"],
                        "kernel_registros": COLETOR_DATASET_DUAL_AE5.contexto()["datasets"]["kernel"]["registros"],
                        "treinamento_automatico": False,
                    },
                },
            )
            return

        if self.path == "/api/ae5/valor":
            if not self._authorized():
                return
            try:
                contexto_ae5 = DESCOBERTA_CONTINUA_AE5.contexto()
            except Exception as erro:
                contexto_ae5 = {
                    "sucesso": False,
                    "estado": "ae5_indisponivel",
                    "origem": DESCOBERTA_CONTINUA_AE5.FONTE,
                    "versao": DESCOBERTA_CONTINUA_AE5.VERSAO,
                    "motivo": str(erro),
                    "autorizacao_explicita": False,
                    "integracao_executada": False,
                    "stable_modificada": False,
                    "arquitetura_modificada": False,
                    "conhecimento_permanente": False,
                }
            self._send_json(200, contexto_ae5)
            return

        if self.path == "/api/ae5/datasets":
            if not self._authorized():
                return
            try:
                contexto_datasets = COLETOR_DATASET_DUAL_AE5.contexto()
            except Exception as erro:
                contexto_datasets = {
                    "sucesso": False,
                    "estado": "coletor_dual_ae5_indisponivel",
                    "origem": COLETOR_DATASET_DUAL_AE5.FONTE,
                    "versao": COLETOR_DATASET_DUAL_AE5.VERSAO,
                    "motivo": str(erro),
                    "treinamento_automatico": False,
                    "implantacao_automatica": False,
                    "invariantes": {
                        "autorizacao_explicita": False,
                        "integracao_executada": False,
                        "stable_modificada": False,
                        "arquitetura_modificada": False,
                        "conhecimento_permanente": False,
                    },
                }
            self._send_json(200, contexto_datasets)
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
    print(
        "[Nyxal-API] TTS principal: "
        f"Kokoro {KOKORO_VOICE}"
    )
    print(
        "[Nyxal-API] endpoint de voz: "
        "POST /api/stt"
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
