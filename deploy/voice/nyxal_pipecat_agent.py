#!/usr/bin/env python3
"""Experimental local real-time voice loop for Nyxal.

Pipecat owns live audio I/O, VAD, barge-in, and streaming local TTS.
Nyxal remains responsible for chat reasoning, capabilities, and conversation
memory through its existing POST /api/chat endpoint.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from dotenv import load_dotenv
from loguru import logger

from nixal_seguranca_http import host_loopback
from nyxal_clap_wake import TwoClapDetector, is_rest_command
from nyxal_voice_prosody import (
    choose_speech_profile,
    clean_speech_text,
    prepare_spoken_reply,
)

# Load user-local settings without overriding values injected by systemd/shell.
import aiohttp
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    AudioRawFrame,
    TranscriptionFrame,
    TTSSpeakFrame,
    TTSUpdateSettingsFrame,
    VADUserStartedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import (
    PipelineParams,
    PipelineWorker,
    ProcessorUnusablePolicy,
)
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.processors.frame_processor import (
    FrameDirection,
    FrameProcessor,
    FrameProcessorSetup,
)
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.whisper.stt import WhisperSTTService
from pipecat.transcriptions.language import Language
from pipecat.transports.local.audio import (
    LocalAudioTransport,
    LocalAudioTransportParams,
)
from pipecat.workers.runner import WorkerRunner


# Load user-local settings without overriding values injected by systemd/shell.
load_dotenv(Path.home() / ".config" / "nyxal" / "nyxal.env", override=False)


def _clamped_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return min(high, max(low, value))


def _spoken_text(value: str) -> str:
    """Clean Markdown and preserve phrase boundaries for natural speech."""
    return clean_speech_text(value)


def _extract_reply(payload: Any) -> str:
    """Read the existing Nyxal /api/chat response contract."""
    if not isinstance(payload, dict):
        return ""

    direct = payload.get("resposta")
    if isinstance(direct, str) and direct.strip():
        return _spoken_text(direct)

    valor = payload.get("valor")
    if isinstance(valor, dict):
        transporte = valor.get("transporte")
        if isinstance(transporte, dict):
            resposta = transporte.get("resposta")
            if isinstance(resposta, dict):
                candidate = resposta.get("resposta")
                if isinstance(candidate, str) and candidate.strip():
                    return _spoken_text(candidate)

        for key in ("resposta", "texto", "mensagem"):
            candidate = valor.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return _spoken_text(candidate)

    return ""


def _voice_mode_command(value: str) -> str | None:
    """Recognize explicit, whole-utterance controls; do not match ordinary prose."""
    command = " ".join(str(value or "").casefold().strip().split()).rstrip(".!?…").strip()
    if command == "modo cena":
        return "cena"
    if command == "corta":
        return "padrao"
    return None


def _quoted_scene_text(value: str) -> str | None:
    """Extract a whole quoted utterance for one-shot dramatic TTS."""
    text = str(value or "").strip()
    if len(text) < 3:
        return None
    closing = {'"': '"', "'": "'", "“": "”", "‘": "’", "«": "»"}
    expected = closing.get(text[0])
    if expected is None or text[-1] != expected:
        return None
    spoken = text[1:-1].strip()
    return spoken or None


def _chat_payload(
    utterance: str,
    session_id: str | None,
    response_mode: str = "padrao",
) -> dict[str, str]:
    """Build a request compatible with the API's server-owned session lifecycle."""
    if not isinstance(response_mode, str) or response_mode not in {"padrao", "cena"}:
        raise ValueError("O perfil de resposta precisa ser 'padrao' ou 'cena'.")
    request = {"mensagem": utterance}
    if isinstance(session_id, str) and session_id.strip():
        request["sessao"] = session_id
    if response_mode == "cena":
        request["perfil_resposta"] = "cena"
    return request


def _returned_session_id(payload: Any, current: str | None) -> str | None:
    """Adopt the session ID created/returned by Nyxal; keep a valid current ID otherwise."""
    candidate = payload.get("sessao") if isinstance(payload, dict) else None
    if isinstance(candidate, str) and candidate.strip():
        return candidate
    return current


def _api_request_headers(api_base: str) -> dict[str, str]:
    """Build chat headers and never send the local API token to a remote host."""
    try:
        parsed = urlsplit(api_base)
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("NYXAL_API_BASE não é uma URL válida.") from exc

    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("NYXAL_API_BASE precisa ser uma URL HTTP(S) sem credenciais, query ou fragmento.")

    if not host_loopback(parsed.hostname):
        raise RuntimeError(
            "NYXAL_API_BASE deve apontar para localhost/loopback; "
            "o adaptador de voz não pode falar com outra instância remota."
        )

    try:
        expected_port = int(os.environ.get("NYXAL_API_PORT", "8010").strip())
    except ValueError as exc:
        raise ValueError("NYXAL_API_PORT precisa ser uma porta numérica válida.") from exc
    if not 1 <= expected_port <= 65535:
        raise ValueError("NYXAL_API_PORT precisa estar entre 1 e 65535.")
    actual_port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    if actual_port != expected_port:
        raise RuntimeError(
            f"NYXAL_API_BASE usa a porta {actual_port}, mas NYXAL_API_PORT={expected_port}; "
            "nenhuma requisição foi enviada."
        )

    headers = {"Accept": "application/json"}
    token = os.environ.get("NYXAL_API_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


class TurnState:
    """Shared generation counter used to discard answers made stale by barge-in."""

    def __init__(self) -> None:
        self.generation = 0
        self.sleeping = True


class ClapWakeProcessor(FrameProcessor):
    """Gate microphone audio until an intentional two-clap wake gesture."""

    def __init__(self, turn_state: TurnState, threshold: float = 0.18) -> None:
        super().__init__()
        self._state = turn_state
        self._claps = TwoClapDetector(threshold=threshold)

    async def process_frame(self, frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if direction == FrameDirection.DOWNSTREAM and isinstance(frame, AudioRawFrame):
            if self._state.sleeping:
                if self._claps.feed(frame.audio):
                    self._state.sleeping = False
                    logger.info("[nyxal-voz] duas palmas detectadas; escuta de conversa ativada")
                # Never send clap or ambient audio to VAD/STT.
                return
        await self.push_frame(frame, direction)


class BargeInProcessor(FrameProcessor):
    """Broadcast an interruption as soon as VAD detects a new user turn."""

    def __init__(self, turn_state: TurnState) -> None:
        super().__init__()
        self._turn_state = turn_state

    async def process_frame(self, frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if (
            direction == FrameDirection.DOWNSTREAM
            and isinstance(frame, VADUserStartedSpeakingFrame)
        ):
            self._turn_state.generation += 1
            logger.info("[nyxal-voz] fala detectada; interrompendo o áudio anterior se estiver ativo")
            # Pipecat removes interruptible queued speech/audio and signals downstream
            # TTS/output processors. The generation counter prevents stale API
            # responses from being spoken after a newer user turn.
            await self.broadcast_interruption()
        await self.push_frame(frame, direction)


class NyxalChatProcessor(FrameProcessor):
    """Bridge final local transcriptions to Nyxal's existing conversational API."""

    def __init__(
        self,
        api_base: str,
        turn_state: TurnState,
        tts: KokoroTTSService,
        base_speed: float,
        session_id: str | None = None,
    ) -> None:
        super().__init__()
        self._api_base = api_base.rstrip("/")
        # A session must be created by /api/chat before the agent can reuse it.
        self._session_id: str | None = session_id
        self._turn_state = turn_state
        self._tts = tts
        self._base_speed = base_speed
        self._voice_mode = "padrao"
        self._http: aiohttp.ClientSession | None = None

    async def setup(self, setup: FrameProcessorSetup) -> None:
        await super().setup(setup)
        timeout = aiohttp.ClientTimeout(total=180, connect=5)
        self._http = aiohttp.ClientSession(timeout=timeout)

    async def cleanup(self) -> None:
        if self._http is not None and not self._http.closed:
            await self._http.close()
        await super().cleanup()

    async def _ask_nyxal(
        self,
        utterance: str,
        response_mode: str = "padrao",
    ) -> str:
        if self._http is None:
            raise RuntimeError("HTTP conversation client is not initialized")

        async with self._http.post(
            f"{self._api_base}/api/chat",
            json=_chat_payload(utterance, self._session_id, response_mode),
            headers=_api_request_headers(self._api_base),
        ) as response:
            if response.status < 200 or response.status >= 300:
                # Read only a non-sensitive state label; never log the transcript/body.
                try:
                    error_payload = await response.json(content_type=None)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                    error_payload = {}
                state = (
                    error_payload.get("estado")
                    if isinstance(error_payload, dict)
                    else None
                )
                suffix = f", estado={state}" if isinstance(state, str) and state else ""
                raise RuntimeError(
                    f"Nyxal API returned HTTP {response.status}{suffix}"
                )
            payload = await response.json(content_type=None)

        reply = _extract_reply(payload)
        if not reply:
            state = payload.get("estado") if isinstance(payload, dict) else None
            suffix = f" (estado={state})" if isinstance(state, str) and state else ""
            raise RuntimeError("Nyxal API returned no usable response text" + suffix)

        session_id = _returned_session_id(payload, self._session_id)
        if not session_id:
            raise RuntimeError("Nyxal API returned a reply without a usable session ID")
        self._session_id = session_id
        return reply

    async def _speak(self, text: str, user_text: str = "", mode: str | None = None) -> None:
        active_mode = self._voice_mode if mode is None else mode
        profile = choose_speech_profile(
            user_text,
            text,
            self._base_speed,
            mode=active_mode,
        )
        spoken_text = prepare_spoken_reply(text, user_text, profile)
        logger.info(
            "[nyxal-voz] perfil de fala={} velocidade={}",
            profile.style,
            profile.speed,
        )
        await self.push_frame(
            TTSUpdateSettingsFrame(
                delta=KokoroTTSService.Settings(speed=profile.speed),
                service=self._tts,
            ),
            FrameDirection.DOWNSTREAM,
        )
        await self.push_frame(
            TTSSpeakFrame(spoken_text),
            FrameDirection.DOWNSTREAM,
        )

    async def process_frame(self, frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if direction == FrameDirection.DOWNSTREAM and isinstance(frame, TranscriptionFrame):
            utterance = frame.text.strip()
            if not utterance:
                return

            if is_rest_command(utterance):
                self._turn_state.generation += 1
                await self._speak(
                    "Certo. Vou entrar em repouso. Duas palmas me despertam.",
                    utterance,
                )
                self._turn_state.sleeping = True
                logger.info("[nyxal-voz] comando verbal de repouso reconhecido")
                return

            voice_command = _voice_mode_command(utterance)
            if voice_command is not None:
                self._turn_state.generation += 1
                self._voice_mode = voice_command
                if voice_command == "cena":
                    acknowledgement = (
                        "Modo Cena ativado. Vou interpretar com mais intenção, "
                        "intensidade e pausas deliberadas."
                    )
                else:
                    acknowledgement = "Corta. Voltei ao modo padrão."
                await self._speak(acknowledgement, mode=voice_command)
                return

            quoted_scene = _quoted_scene_text(utterance)
            if quoted_scene is not None:
                self._turn_state.generation += 1
                await self._speak(quoted_scene, mode="cena")
                return

            generation_at_request = self._turn_state.generation
            api_request_started_at = time.perf_counter()
            logger.info("[nyxal-voz] transcrição concluída; consultando o núcleo conversacional")
            try:
                reply = await self._ask_nyxal(utterance, self._voice_mode)
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, ValueError) as error:
                detail = str(error).strip()
                logger.error(
                    "[nyxal-voz] falha ao acessar o núcleo: {}",
                    detail[:240] if detail else type(error).__name__,
                )
                reply = "Não consegui acessar o núcleo da Nyxal agora. Tente falar novamente."

            elapsed_ms = round((time.perf_counter() - api_request_started_at) * 1000)
            logger.info("[nyxal-voz] tempo até resposta completa do núcleo: {} ms", elapsed_ms)

            # A newer voice turn may have started while the API was responding.
            # Never play an answer to an utterance that the user has already interrupted.
            if generation_at_request != self._turn_state.generation:
                logger.info("[nyxal-voz] resposta antiga descartada após nova fala")
                return

            if reply:
                logger.info("[nyxal-voz] iniciando reprodução de voz")
                await self._speak(reply, utterance)
            return

        await self.push_frame(frame, direction)


async def _check_api(api_base: str) -> None:
    timeout = aiohttp.ClientTimeout(total=5, connect=3)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            f"{api_base.rstrip('/')}/health",
            headers=_api_request_headers(api_base),
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"Nyxal API health returned HTTP {response.status}")
            await response.read()


async def main() -> None:
    # Keep logs to states/errors only. Never log speech transcripts or response text.
    logger.remove()
    logger.add(sys.stderr, level=os.environ.get("NYXAL_PIPECAT_LOG_LEVEL", "INFO"))

    api_base = os.environ.get("NYXAL_API_BASE", "http://127.0.0.1:8010")
    voice = os.environ.get("NYXAL_KOKORO_VOICE", "pf_dora").strip()
    model = os.environ.get(
        "NYXAL_PIPECAT_WHISPER_MODEL",
        os.environ.get("NYXAL_WHISPER_MODEL", "base"),
    ).strip()
    speed = _clamped_float("NYXAL_KOKORO_SPEED", 1.0, 0.75, 1.25)

    if not voice:
        raise RuntimeError("NYXAL_KOKORO_VOICE cannot be empty")

    await _check_api(api_base)
    logger.info("[nyxal-voz] API local disponível; preparando pipeline de voz")
    logger.info("[nyxal-voz] STT local Whisper model={} · TTS local Kokoro voice={}", model, voice)
    logger.info("[nyxal-voz] modelos ficam no cache local; não são incluídos no Git")

    # Nyxal creates the first session in /api/chat and returns its real ID.
    # The processor adopts it and reuses it on later turns in this run.
    turn_state = TurnState()

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )
    vad = VADProcessor(
        vad_analyzer=SileroVADAnalyzer(),
        audio_idle_timeout=1.0,
    )
    barge_in = BargeInProcessor(turn_state)
    clap_wake = ClapWakeProcessor(
        turn_state,
        threshold=_clamped_float("NYXAL_CLAP_THRESHOLD", 0.18, 0.08, 0.85),
    )

    stt = WhisperSTTService(
        device="cpu",
        compute_type="int8",
        settings=WhisperSTTService.Settings(
            model=model,
            language=Language.PT,
            no_speech_prob=0.6,
            hotwords="Nyxal Nixal Nixau NyxOS Ollama Kokoro Qwen",
            initial_prompt="Conversa natural em português brasileiro sobre a assistente Nyxal (pronuncia-se Nixal) e o sistema NyxOS.",
        ),
    )
    tts = KokoroTTSService(
        settings=KokoroTTSService.Settings(
            voice=voice,
            language=Language.PT_BR,
            speed=speed,
        ),
    )
    chat = NyxalChatProcessor(api_base, turn_state, tts, speed)

    pipeline = Pipeline(
        [
            transport.input(),
            clap_wake,
            vad,
            barge_in,
            stt,
            chat,
            tts,
            transport.output(),
        ]
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        processor_unusable_policy=ProcessorUnusablePolicy.END,
    )
    runner = WorkerRunner()
    await runner.add_workers(worker)

    logger.info("[nyxal-voz] modo repouso; duas palmas próximas ativam a conversa")
    logger.info("[nyxal-voz] em conversa, nova fala interrompe a resposta anterior")
    await runner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[nyxal-voz] encerrado pelo usuário", file=sys.stderr)
