#!/usr/bin/env python3

import json
import mimetypes
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import compare_digest, token_urlsafe

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
from nixal_estado_presenca import compor_presenca_efetiva
from nixal_descoberta_continua_ae5 import DescobertaContinuaGovernadaAE5
from nixal_coletor_dataset_dual_ae5 import ColetorDatasetDualAE5
from nixal_vps import VpsNyxOS
from nixal_amd_developer_cloud import AmdDeveloperCloud
from nixal_display_routes import resolve_display_file
from nixal_agent_hub import NyxalAgentHub
from nixal_observabilidade_sistema import ObservabilidadeSistemaNixOS
from nixal_integracao_gmail import IntegracaoGmailNixOS
from nixal_capacidade_visual import CapacidadeVisualGeminiNixOS
from urllib.parse import parse_qs, urlsplit

from nixal_seguranca_http import (
    host_loopback,
    origin_permitida,
    parse_allowed_origins,
)


BASE_DIR = Path(__file__).resolve().parent
HOST = os.environ.get("NYXAL_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("NYXAL_API_PORT", "8010"))
API_TOKEN = os.environ.get("NYXAL_API_TOKEN", "")
CORS_ORIGINS = parse_allowed_origins(
    os.environ.get(
        "NYXAL_API_CORS_ORIGINS",
        os.environ.get("NYXAL_API_CORS_ORIGIN"),
    ),
    default_origins={
        f"http://127.0.0.1:{PORT}",
        f"http://localhost:{PORT}",
        f"http://[::1]:{PORT}",
    },
)
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
VPS_NYXOS = VpsNyxOS()
AMD_DEVELOPER_CLOUD = AmdDeveloperCloud()
AGENTE_NYXAL = NyxalAgentHub()
OBSERVABILIDADE_NYXOS = ObservabilidadeSistemaNixOS()
GMAIL_NYXOS = IntegracaoGmailNixOS()
CAPACIDADE_VISUAL_NYXOS = CapacidadeVisualGeminiNixOS()
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


def _precisa_contexto_sistema(mensagem: str) -> bool:
    texto = mensagem.lower()
    termos = (
        "sistema", "pc", "cpu", "ram", "memória", "memoria", "processo",
        "serviço", "servico", "serviços", "servicos", "recursos", "ocorrendo",
        "acontecendo", "computador", "máquina", "maquina", "notebook", "rodando",
        "funcionando", "travando", "lento", "temperatura", "disco", "armazenamento",
        "hardware", "saúde", "saude", "status do", "estado do", "residência",
        "residencia", "uso da", "uso do", "presença", "presenca", "nyxos",
    )
    return any(termo in texto for termo in termos)


def _precisa_contexto_email(mensagem: str) -> bool:
    texto = mensagem.lower()
    return any(termo in texto for termo in (
        "email", "e-mail", "gmail", "caixa de entrada", "inbox",
        "correio eletrônico", "correio eletronico", "meus e-mails",
        "meus emails", "mensagens do email", "mensagem do email",
    ))


def _precisa_contexto_agenda(mensagem: str) -> bool:
    texto = mensagem.lower()
    return any(termo in texto for termo in (
        "agenda", "calendário", "calendario", "compromisso", "compromissos",
        "reunião", "reuniao", "evento", "eventos", "horário de hoje",
        "horario de hoje", "o que tenho hoje", "próxima reunião",
        "proxima reuniao",
    ))


def _precisa_contexto_contatos(mensagem: str) -> bool:
    texto = mensagem.lower()
    return any(termo in texto for termo in (
        "contato", "contatos", "telefone de", "email de", "e-mail de",
        "endereço de e-mail", "endereco de email", "número de", "numero de",
    ))


def _precisa_contexto_drive(mensagem: str) -> bool:
    texto = mensagem.lower()
    return any(termo in texto for termo in (
        "google drive", "drive", "arquivo no google", "arquivos do drive",
        "documento no drive", "documentos no drive", "meus documentos",
    ))


def json_bytes(payload: dict) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")


def read_local_json(nome_arquivo: str) -> dict:
    caminho = BASE_DIR / nome_arquivo
    if not caminho.exists():
        return {}
    try:
        valor = json.loads(caminho.read_text(encoding="utf-8"))
        return valor if isinstance(valor, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def read_machine_presence() -> dict:
    """Lê a presença residente do arquivo atualizado pelo próprio ciclo."""
    try:
        return PresencaMaquinaNixOS(
            arquivo=BASE_DIR / "presenca_maquina_nyxos.json"
        ).contexto()
    except Exception as erro:
        return {
            "sucesso": False,
            "estado": "presenca_maquina_indisponivel",
            "origem": "presenca_maquina_nyxos",
            "motivo": f"{type(erro).__name__}: {erro}",
        }


def read_nyxos_contexto() -> dict:
    return {
        "sucesso": True,
        "estado": "nyxos_contexto_disponivel",
        "origem": "nyxos_contexto_residente",
        "corpo": read_local_json("estado_corpo_nixal.json"),
        "fisiologia": read_local_json("fisiologia_operacional_nyxos.json"),
        "plano_central_controle": read_local_json("plano_central_controle_nyxos.json"),
        "gateway_atuacao": read_local_json("gateway_atuacao_nyxos.json"),
        "runtime": read_local_json("estado_nyxal_runtime.json"),
        "governanca": {
            "execucao_fisica_habilitada": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        },
    }


def caminho_interface(relativo: str) -> Path | None:
    raiz = (BASE_DIR / "interface").resolve()
    candidato = (raiz / relativo).resolve()
    try:
        candidato.relative_to(raiz)
    except ValueError:
        return None
    return candidato if candidato.is_file() else None


def caminho_display(relativo: str) -> Path | None:
    raiz = (BASE_DIR / "interface" / "display" / "dist").resolve()
    candidato = (raiz / relativo).resolve()
    try:
        candidato.relative_to(raiz)
    except ValueError:
        return None
    return candidato if candidato.is_file() else None


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



RESIDENCIA_UNIDADES = (
    "nyxos.target",
    "nyxal-api.service",
    "nyxos-residente.service",
    "nyxos-interface.service",
)

def residencia_snapshot() -> dict:
    unidades = []
    for nome in RESIDENCIA_UNIDADES:
        try:
            resultado = subprocess.run(
                ["systemctl", "--user", "show", nome, "--property=ActiveState,SubState,LoadState,MainPID,MemoryCurrent,CPUUsageNSec,UnitFileState,Description"],
                capture_output=True, text=True, timeout=3, check=False,
            )
            valores = {}
            for linha in resultado.stdout.splitlines():
                chave, separador, valor = linha.partition('=')
                if separador:
                    valores[chave] = valor
            active = valores.get("ActiveState", "unknown")
            substate = valores.get("SubState", "unknown")
            pid = int(valores.get("MainPID", "0") or 0)
            memory_bytes = int(valores.get("MemoryCurrent", "0") or 0)
            unidades.append({
                "name": nome,
                "description": valores.get("Description", nome),
                "status": active,
                "subState": substate,
                "loadState": valores.get("LoadState", "unknown"),
                "pid": pid or None,
                "memoryUsageMb": round(memory_bytes / 1024 / 1024, 2) if memory_bytes else 0,
                "cpuUsagePct": None,
                "enabled": valores.get("UnitFileState") in {"enabled", "static", "alias", "linked"},
            })
        except (OSError, ValueError, subprocess.TimeoutExpired) as erro:
            unidades.append({"name": nome, "description": nome, "status": "unknown", "subState": "unavailable", "loadState": "unknown", "pid": None, "memoryUsageMb": 0, "cpuUsagePct": None, "enabled": False, "erro": str(erro)})
    return {
        "sucesso": True,
        "estado": "residencia_observada",
        "origem": "systemd_user",
        "target": "nyxos.target",
        "unidades": unidades,
        "modo": "somente_leitura",
    }
class NyxalAPIHandler(BaseHTTPRequestHandler):
    server_version = "NyxalAPI"
    sys_version = ""

    def _send_security_headers(self) -> None:
        """Emite cabeçalhos defensivos e CORS apenas para origens permitidas."""
        origin = self.headers.get("Origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        if origin is not None and origin_permitida(origin, CORS_ORIGINS):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header(
                "Access-Control-Allow-Headers",
                "Authorization, Content-Type",
            )
            self.send_header(
                "Access-Control-Allow-Methods",
                "GET, POST, OPTIONS",
            )

    def _origem_api_permitida(self) -> bool:
        """Bloqueia origens web não autorizadas antes de acessar dados locais."""
        parsed_path = urlsplit(self.path).path
        origin = self.headers.get("Origin")
        if not parsed_path.startswith("/api/") or origin is None:
            return True
        if origin_permitida(origin, CORS_ORIGINS):
            return True
        self._send_json(
            403,
            {
                "estado": "origem_nao_permitida",
                "motivo": "A origem web não está na lista de origens autorizadas.",
            },
        )
        return False

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
        self._send_security_headers()
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
        self._send_security_headers()
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

    def _local_ou_autorizado(self) -> bool:
        endereco = self.client_address[0] if self.client_address else ""
        if endereco in {"127.0.0.1", "::1"}:
            return True
        return self._authorized()

    def do_OPTIONS(self) -> None:
        if not self._origem_api_permitida():
            return
        self.send_response(204)
        self._send_security_headers()
        self.end_headers()

    def do_POST(self) -> None:
        if not self._origem_api_permitida():
            return
        if (
            urlsplit(self.path).path.startswith("/api/")
            and not self._local_ou_autorizado()
        ):
            return

        if self.path == "/api/agent/image":
            if not self._local_ou_autorizado():
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(400, {"estado": "entrada_invalida", "motivo": "Content-Length inválido."})
                return
            if content_length <= 0 or content_length > 12 * 1024 * 1024:
                self._send_json(400 if content_length <= 0 else 413, {
                    "estado": "entrada_visual_invalida",
                    "motivo": "O pedido deve conter JSON e não pode exceder 12 MiB.",
                })
                return
            try:
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"estado": "entrada_visual_invalida", "motivo": "JSON UTF-8 inválido."})
                return
            if not isinstance(payload, dict):
                self._send_json(400, {"estado": "entrada_visual_invalida", "motivo": "O corpo precisa ser um objeto JSON."})
                return
            try:
                result = CAPACIDADE_VISUAL_NYXOS.gerar_ou_editar(
                    prompt=payload.get("prompt", ""),
                    imagem_base64=payload.get("imagem_base64"),
                    mime_type=payload.get("mime_type"),
                )
                self._send_json(200, result)
            except ValueError as erro:
                self._send_json(400, {"estado": "entrada_visual_invalida", "motivo": str(erro)})
            except RuntimeError as erro:
                self._send_json(503, {"estado": "capacidade_visual_indisponivel", "motivo": str(erro)})
            except Exception as erro:
                self._send_json(502, {"estado": "falha_visual", "motivo": f"{type(erro).__name__}: operação visual indisponível."})
            return

        if self.path == "/api/amd-cloud/check":
            if not self._authorized():
                return
            resultado = AMD_DEVELOPER_CLOUD.verificar_conexao()
            self._send_json(200 if resultado.get("sucesso") else 503, resultado)
            return

        if self.path in {"/api/vps/action", "/api/vps/provisionar"}:
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(400, {"estado": "entrada_invalida", "motivo": "Content-Length inválido."})
                return

            if content_length <= 0 or content_length > 32 * 1024:
                self._send_json(400 if content_length <= 0 else 413, {
                    "estado": "entrada_invalida",
                    "motivo": "Payload VPS inválido.",
                })
                return

            try:
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"estado": "entrada_invalida", "motivo": "JSON VPS inválido."})
                return

            if not isinstance(payload, dict):
                self._send_json(400, {"estado": "entrada_invalida", "motivo": "Payload VPS precisa ser objeto."})
                return

            try:
                if self.path == "/api/vps/action":
                    resultado = VPS_NYXOS.action(
                        nome=payload.get("nome"),
                        acao=payload.get("acao"),
                    )
                else:
                    resultado = VPS_NYXOS.provisionar(
                        nome=payload.get("nome"),
                        image_path=payload.get("image_path"),
                        memory_mb=payload.get("memory_mb", 2048),
                        vcpus=payload.get("vcpus", 2),
                        disk_gb=payload.get("disk_gb", 20),
                        autostart=payload.get("autostart", True),
                        username=payload.get("username", "ubuntu"),
                        ssh_public_key=payload.get("ssh_public_key"),
                    )
                self._send_json(200 if resultado.get("sucesso") else 422, resultado)
            except (TypeError, ValueError, FileNotFoundError, FileExistsError) as erro:
                self._send_json(400, {"estado": "entrada_vps_invalida", "motivo": str(erro)})
            except Exception as erro:
                self._send_json(500, {"estado": "erro_vps", "motivo": str(erro)})
            return

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

        if self.path not in {"/api/chat", "/api/agent/chat"}:
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
        if self.path == "/api/agent/chat" and sessao_id is None:
            sessao_id = token_urlsafe(18)

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

        if self.path == "/api/agent/chat":
            provedor = payload.get("provedor", os.environ.get("NYXAL_AGENT_PROVIDER", "auto"))
            if not isinstance(provedor, str):
                self._send_json(400, {"estado": "provedor_invalido", "motivo": "O campo provedor precisa ser texto."})
                return
            try:
                provedor_resolvido = AGENTE_NYXAL.resolve_provider(provedor)
                if provedor_resolvido != "nyxal":
                    contexto_sistema = {}
                    if _precisa_contexto_sistema(mensagem):
                        contexto_sistema["observabilidade"] = OBSERVABILIDADE_NYXOS.snapshot()
                        contexto_sistema["residencia"] = residencia_snapshot()
                    if _precisa_contexto_email(mensagem):
                        try:
                            status_google = GMAIL_NYXOS.status()
                            contexto_sistema["gmail"] = (
                                GMAIL_NYXOS.listar_mensagens(query="is:unread newer_than:7d", limite=10)
                                if status_google.get("servicos_disponiveis", {}).get("gmail") and status_google.get("estado") == "configurado"
                                else status_google
                            )
                        except Exception:
                            contexto_sistema["gmail"] = {
                                "estado": "gmail_indisponivel", "somente_leitura": True,
                                "motivo": "Não foi possível consultar o Gmail nesta solicitação.",
                            }
                    if _precisa_contexto_agenda(mensagem):
                        try:
                            contexto_sistema["agenda"] = GMAIL_NYXOS.listar_eventos(limite=12, dias=14)
                        except Exception:
                            contexto_sistema["agenda"] = {"estado": "agenda_indisponivel", "somente_leitura": True}
                    if _precisa_contexto_contatos(mensagem):
                        try:
                            contexto_sistema["contatos"] = GMAIL_NYXOS.listar_contatos(limite=25)
                        except Exception:
                            contexto_sistema["contatos"] = {"estado": "contatos_indisponiveis", "somente_leitura": True}
                    if _precisa_contexto_drive(mensagem):
                        try:
                            contexto_sistema["google_drive"] = GMAIL_NYXOS.listar_arquivos_drive(limite=25)
                        except Exception:
                            contexto_sistema["google_drive"] = {"estado": "drive_indisponivel", "somente_leitura": True}
                    resposta_agente = AGENTE_NYXAL.responder(
                        mensagem,
                        sessao=sessao_id,
                        provedor=provedor,
                        contexto_sistema=contexto_sistema,
                    )
                    if not resposta_agente.get("fallback_local"):
                        self._send_json(200, resposta_agente)
                        return
            except ValueError as erro:
                self._send_json(400, {"estado": "provedor_invalido", "motivo": str(erro)})
                return
            except RuntimeError as erro:
                self._send_json(503, {"estado": "provedor_indisponivel", "motivo": str(erro)})
                return
            except Exception as erro:
                self._send_json(502, {"estado": "falha_no_agente", "motivo": f"{type(erro).__name__}: integração indisponível."})
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
        parsed_path = urlsplit(self.path).path
        if not self._origem_api_permitida():
            return
        if parsed_path.startswith("/api/") and not self._local_ou_autorizado():
            return
        is_agent_or_workspace = (
            parsed_path in {"/api/agent/status", "/api/agent/contexto", "/api/integracoes/google/status", "/api/integracoes/gmail/status"}
            or parsed_path.startswith("/api/integracoes/google/")
            or parsed_path.startswith("/api/integracoes/gmail/")
        )
        if is_agent_or_workspace and not self._local_ou_autorizado():
            return

        if self.path == "/":
            caminho = caminho_display("index.html") or caminho_interface("index.html")
            if caminho is None:
                self._send_json(404, {"estado": "interface_indisponivel"})
                return
            corpo = caminho.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)
            return

        if parsed_path == "/display" or parsed_path.startswith("/display/"):
            relativo = parsed_path.removeprefix("/display/") if parsed_path.startswith("/display/") else ""
            relativo = relativo.lstrip("/") or "index.html"
            caminho = resolve_display_file(BASE_DIR / "interface" / "display" / "dist", self.path)
            if caminho is None:
                self._send_json(404, {"estado": "display_arquivo_nao_encontrado", "arquivo": relativo})
                return
            corpo = caminho.read_bytes()
            tipo = mimetypes.guess_type(str(caminho))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)
            return

        if self.path.startswith("/interface/"):
            relativo = self.path.removeprefix("/interface/")
            caminho = caminho_interface(relativo)
            if caminho is None:
                self._send_json(404, {"estado": "arquivo_interface_nao_encontrado"})
                return
            corpo = caminho.read_bytes()
            tipo = mimetypes.guess_type(str(caminho))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)
            return

        if parsed_path == "/api/agent/status":
            status_agente = AGENTE_NYXAL.contexto()
            status_agente["criacao_visual"] = CAPACIDADE_VISUAL_NYXOS.status()
            self._send_json(200, status_agente)
            return

        if parsed_path == "/api/agent/contexto":
            self._send_json(200, {
                "sucesso": True,
                "estado": "contexto_observado",
                "origem": "nyxal_agent_context",
                "observabilidade": OBSERVABILIDADE_NYXOS.snapshot(),
                "residencia": residencia_snapshot(),
            })
            return

        if parsed_path == "/api/integracoes/google/status":
            self._send_json(200, GMAIL_NYXOS.status())
            return

        if parsed_path == "/api/integracoes/google/agenda":
            query = parse_qs(urlsplit(self.path).query)
            try:
                self._send_json(200, GMAIL_NYXOS.listar_eventos(
                    limite=int(query.get("limit", ["20"])[0]),
                    dias=int(query.get("days", ["14"])[0]),
                ))
            except ValueError as erro:
                self._send_json(400, {"estado": "entrada_google_invalida", "motivo": str(erro)})
            except RuntimeError as erro:
                self._send_json(503, {"estado": "google_workspace_indisponivel", "motivo": str(erro)})
            except Exception as erro:
                self._send_json(502, {"estado": "google_workspace_falhou", "motivo": f"{type(erro).__name__}: consulta indisponível."})
            return

        if parsed_path == "/api/integracoes/google/contatos":
            query = parse_qs(urlsplit(self.path).query)
            try:
                self._send_json(200, GMAIL_NYXOS.listar_contatos(
                    limite=int(query.get("limit", ["25"])[0]),
                ))
            except ValueError as erro:
                self._send_json(400, {"estado": "entrada_google_invalida", "motivo": str(erro)})
            except RuntimeError as erro:
                self._send_json(503, {"estado": "google_workspace_indisponivel", "motivo": str(erro)})
            except Exception as erro:
                self._send_json(502, {"estado": "google_workspace_falhou", "motivo": f"{type(erro).__name__}: consulta indisponível."})
            return

        if parsed_path == "/api/integracoes/google/drive":
            query = parse_qs(urlsplit(self.path).query)
            try:
                self._send_json(200, GMAIL_NYXOS.listar_arquivos_drive(
                    limite=int(query.get("limit", ["25"])[0]),
                ))
            except ValueError as erro:
                self._send_json(400, {"estado": "entrada_google_invalida", "motivo": str(erro)})
            except RuntimeError as erro:
                self._send_json(503, {"estado": "google_workspace_indisponivel", "motivo": str(erro)})
            except Exception as erro:
                self._send_json(502, {"estado": "google_workspace_falhou", "motivo": f"{type(erro).__name__}: consulta indisponível."})
            return

        if parsed_path == "/api/integracoes/gmail/status":
            self._send_json(200, GMAIL_NYXOS.status())
            return

        if parsed_path == "/api/integracoes/gmail/mensagens":
            query = parse_qs(urlsplit(self.path).query)
            try:
                self._send_json(200, GMAIL_NYXOS.listar_mensagens(
                    query=query.get("q", ["is:unread newer_than:7d"])[0],
                    limite=int(query.get("limit", ["10"])[0]),
                ))
            except ValueError as erro:
                self._send_json(400, {"estado": "entrada_gmail_invalida", "motivo": str(erro)})
            except RuntimeError as erro:
                self._send_json(503, {"estado": "gmail_indisponivel", "motivo": str(erro)})
            except Exception as erro:
                self._send_json(502, {"estado": "falha_gmail", "motivo": f"{type(erro).__name__}: consulta indisponível."})
            return

        if parsed_path == "/api/integracoes/gmail/mensagem":
            query = parse_qs(urlsplit(self.path).query)
            try:
                self._send_json(200, GMAIL_NYXOS.obter_mensagem(query.get("id", [""])[0]))
            except ValueError as erro:
                self._send_json(400, {"estado": "entrada_gmail_invalida", "motivo": str(erro)})
            except RuntimeError as erro:
                self._send_json(503, {"estado": "gmail_indisponivel", "motivo": str(erro)})
            except Exception as erro:
                self._send_json(502, {"estado": "falha_gmail", "motivo": f"{type(erro).__name__}: consulta indisponível."})
            return

        if self.path == "/api/amd-cloud/status":
            self._send_json(200, AMD_DEVELOPER_CLOUD.status())
            return

        if self.path == "/api/vps/status":
            self._send_json(200, VPS_NYXOS.status())
            return

        if self.path == "/api/vps/instances":
            self._send_json(200, VPS_NYXOS.instances())
            return

        if self.path == "/api/vps/contexto":
            self._send_json(200, VPS_NYXOS.contexto())
            return

        if self.path == "/api/public/nyxos/contexto":
            self._send_json(200, read_nyxos_contexto())
            return

        if self.path == "/api/public/residencia":
            self._send_json(200, residencia_snapshot())
            return

        if self.path == "/api/public/delta":
            self._send_json(200, {"sucesso": True, "estado": "delta_disponivel", "eventos": DELTA_NYXOS.listar(100), "quantidade": DELTA_NYXOS.quantidade()})
            return

        if self.path == "/api/public/dataset":
            self._send_json(200, COLETOR_DATASET_DUAL_AE5.contexto())
            return

        if self.path == "/api/public/presenca":
            self._send_json(200, read_machine_presence())
            return

        if self.path == "/api/public/recursos":
            self._send_json(200, RECURSOS_HABITAT.snapshot())
            return

        if self.path == "/api/public/operacional":
            self._send_json(200, PERSISTENCIA_OPERACIONAL.contexto())
            return

        if self.path == "/api/public/gateway":
            contexto = read_nyxos_contexto()
            self._send_json(200, {"sucesso": True, "estado": "gateway_contexto_disponivel", "gateway": contexto.get("gateway_atuacao", {}), "plano_central_controle": contexto.get("plano_central_controle", {}), "governanca": contexto.get("governanca", {})})
            return

        if self.path == "/api/public/ae5":
            self._send_json(200, {"descoberta": DESCOBERTA_CONTINUA_AE5.contexto(), "datasets": COLETOR_DATASET_DUAL_AE5.contexto()})
            return

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

            presenca_maquina = read_machine_presence()

            try:
                # A API é independente do processo residente; recarrega o
                # snapshot para não publicar um estado em memória antigo.
                persistencia_operacional = PERSISTENCIA_OPERACIONAL.recarregar()
            except Exception as erro:
                persistencia_operacional = {
                    "sucesso": False,
                    "estado": "persistencia_operacional_indisponivel",
                    "origem": PERSISTENCIA_OPERACIONAL.FONTE,
                    "versao": PERSISTENCIA_OPERACIONAL.VERSAO,
                    "motivo": str(erro),
                }

            presenca_efetiva = compor_presenca_efetiva(
                presenca_legada=presenca,
                estado_legado=estado_operacional,
                presenca_maquina=presenca_maquina,
                persistencia_operacional=persistencia_operacional,
            )

            if presenca_efetiva.get("ativa"):
                estado_publicado = {
                    "modo": (
                        "residente"
                        if presenca_efetiva.get("origem") == "presenca_maquina_nyxos"
                        else estado_operacional.get("modo")
                    ),
                    "status": "ativa",
                }
            else:
                status_legado = str(
                    estado_operacional.get("status") or ""
                ).strip().lower()
                legado_ja_encerrado = status_legado in {
                    "encerrada",
                    "encerrado",
                    "inativa",
                    "inativo",
                    "erro",
                    "falhou",
                }
                estado_publicado = {
                    "modo": (
                        estado_operacional.get("modo")
                        if legado_ja_encerrado
                        else "sem_sinal_recente"
                    ),
                    "status": (
                        estado_operacional.get("status")
                        if legado_ja_encerrado
                        else "inativa"
                    ),
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
                    "presenca": presenca_efetiva,
                    "presenca_legada": {
                        "ativa": presenca.get("ativa"),
                        "ultimo_ciclo": presenca.get("ultimo_ciclo"),
                        "ciclos": presenca.get("ciclos"),
                    },
                    "presenca_maquina": presenca_maquina,
                    "estado": estado_publicado,
                    "estado_legado": {
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
    if not host_loopback(HOST):
        raise RuntimeError(
            "A API HTTP da Nyxal só pode escutar em loopback. "
            "Para acesso remoto, mantenha NYXAL_API_HOST=127.0.0.1 e "
            "use uma VPN ou proxy reverso com TLS e autenticação na borda."
        )

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
