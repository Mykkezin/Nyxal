"""Two-clap wake detector and explicit Portuguese rest commands."""

from __future__ import annotations

import math
import re
import struct
import time
import unicodedata


def _normalized(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in folded if not unicodedata.combining(c)).split())


def is_rest_command(text: str) -> bool:
    value = " ".join(re.sub(r"[,.!?;:]+", " ", _normalized(text)).split())
    # Whisper can render the synthetic Brazilian pronunciation as "Nixau".
    value = re.sub(r"\b(?:nixau|nixal|nicsal)\b", "nyxal", value)
    commands = (
        "nyxal pode descansar", "nyxal entre em repouso", "nyxal va dormir",
        "nyxal dormir", "pode descansar nyxal", "entre em repouso nyxal",
        "va dormir nyxal", "parar de ouvir", "entre em repouso",
    )
    return value in commands


class TwoClapDetector:
    """Detect two sharp, loud peaks separated by a human clap interval."""

    def __init__(self, threshold: float = 0.18, min_interval: float = 0.12,
                 max_interval: float = 0.95, refractory: float = 0.18) -> None:
        self.threshold = threshold
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.refractory = refractory
        self._first: float | None = None
        self._last_peak = 0.0

    def feed(self, pcm: bytes, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if len(pcm) < 4:
            return False
        count = len(pcm) // 2
        values = struct.unpack_from(f"<{count}h", pcm)
        peak = max(abs(v) for v in values) / 32768.0
        rms = math.sqrt(sum(v * v for v in values) / count) / 32768.0
        # Reject sustained speech/noise: clap frames have a sharp transient.
        sharp = peak >= self.threshold and peak >= max(0.08, rms * 2.4)
        if not sharp or now - self._last_peak < self.refractory:
            if self._first is not None and now - self._first > self.max_interval:
                self._first = None
            return False
        self._last_peak = now
        if self._first is None:
            self._first = now
            return False
        interval = now - self._first
        self._first = now if interval < self.min_interval else None
        return self.min_interval <= interval <= self.max_interval
