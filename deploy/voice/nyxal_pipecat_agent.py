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
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Load user-local settings without overriding values injected by systemd/shell.
load_dotenv(Path.home() / ".config" / "nyxal" / "nyxal.env", override=False)

import aiohttp
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TranscriptionFrame, TTSSpeakFrame, VADUserStartedSpeakingFrame
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


def _clamped_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return min(high, max(low, value))


def _spoken_text(value: str) -> str:
    """Remove common Markdown decoration before local TTS, preserving wording."""
    text = re.sub(r"```.*?```", " Omiti um bloco de código da resposta. ", value, flags=re.S)
    text = re.sub(r"`([^\`]+)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}(?:[-*+]\s+|\d+[.)]\s+)", "", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", text)
    text = re.sub(r"[*_~]{1,3}", "", text)
    return re.sub(r"\s+", " ", text).strip()


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


class TurnState:
    """Shared generation counter used to discard answers made stale by barge-in."""

    def __init__(self) -> None:
        self.generation = 0


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

    def __init__(self, api_base: str, session_id: str, turn_state: TurnState) -> None:
        super().__init__()
        self._api_base = api_base.rstrip("/")
        self._session_id = session_id
        self._turn_state = turn_state
        self._http: aiohttp.ClientSession | None = None

    async def setup(self, setup: FrameProcessorSetup) -> None:
        await super().setup(setup)
        timeout = aiohttp.ClientTimeout(total=180, connect=5)
        self._http = aiohttp.ClientSession(timeout=timeout)

    async def cleanup(self) -> None:
        if self._http is not None and not self._http.closed:
            await self._http.close()
        await super().cleanup()

    async def _ask_nyxal(self, utterance: str) -> str:
        if self._http is None:
            raise RuntimeError("HTTP conversation client is not initialized")

        async with self._http.post(
            f"{self._api_base}/api/chat",
            json={"mensagem": utterance, "sessao": self._session_id},
            headers={"Accept": "application/json"},
        ) as response:
            if response.status < 200 or response.status >= 300:
                # Do not log the transcript or the response body.
                raise RuntimeError(f"Nyxal API returned HTTP {response.status}")
            payload = await response.json(content_type=None)

        reply = _extract_reply(payload)
        if not reply:
            raise RuntimeError("Nyxal API returned no usable response text")
        return reply

    async def process_frame(self, frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if direction == FrameDirection.DOWNSTREAM and isinstance(frame, TranscriptionFrame):
            utterance = frame.text.strip()
            if not utterance:
                return

            generation_at_request = self._turn_state.generation
            logger.info("[nyxal-voz] transcrição concluída; consultando o núcleo conversacional")
            try:
                reply = await self._ask_nyxal(utterance)
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, ValueError) as error:
                logger.error(
                    "[nyxal-voz] falha ao obter resposta da API ({})",
                    type(error).__name__,
                )
                reply = "Não consegui acessar o núcleo da Nyxal agora. Tente falar novamente."

            # A newer voice turn may have started while the API was responding.
            # Never play an answer to an utterance that the user has already interrupted.
            if generation_at_request != self._turn_state.generation:
                logger.info("[nyxal-voz] resposta antiga descartada após nova fala")
                return

            if reply:
                logger.info("[nyxal-voz] iniciando reprodução de voz")
                await self.push_frame(
                    TTSSpeakFrame(reply),
                    FrameDirection.DOWNSTREAM,
                )
            return

        await self.push_frame(frame, direction)


async def _check_api(api_base: str) -> None:
    timeout = aiohttp.ClientTimeout(total=5, connect=3)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{api_base.rstrip('/')}/health") as response:
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
    speed = _clamped_float("NYXAL_KOKORO_SPEED", 1.03, 0.75, 1.25)

    if not voice:
        raise RuntimeError("NYXAL_KOKORO_VOICE cannot be empty")

    await _check_api(api_base)
    logger.info("[nyxal-voz] API local disponível; preparando pipeline de voz")
    logger.info("[nyxal-voz] STT local Whisper model={} · TTS local Kokoro voice={}", model, voice)
    logger.info("[nyxal-voz] modelos ficam no cache local; não são incluídos no Git")

    # Use the same existing Nyxal conversation session for all turns in this run.
    session_id = "desktop-voice-" + uuid.uuid4().hex
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

    stt = WhisperSTTService(
        model=model,
        device="cpu",
        compute_type="int8",
        language=Language.PT,
        settings=WhisperSTTService.Settings(
            model=model,
            language=Language.PT,
            hotwords="Nyxal NyxOS Ollama Kokoro Qwen",
            initial_prompt="Conversa natural em português brasileiro sobre a assistente Nyxal e o sistema NyxOS.",
        ),
    )
    chat = NyxalChatProcessor(api_base, session_id, turn_state)
    tts = KokoroTTSService(
        settings=KokoroTTSService.Settings(
            voice=voice,
            language=Language.PT_BR,
            speed=speed,
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
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

    logger.info("[nyxal-voz] ouvindo continuamente; Ctrl+C encerra o teste")
    logger.info("[nyxal-voz] fale naturalmente; uma nova fala deve interromper a resposta anterior")
    await runner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[nyxal-voz] encerrado pelo usuário", file=sys.stderr)
