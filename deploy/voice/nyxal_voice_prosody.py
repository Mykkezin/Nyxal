#!/usr/bin/env python3
"""Context-sensitive Brazilian Portuguese speech shaping for Nyxal.

This module is deliberately standard-library-only so its behavior can be tested
without a microphone, model downloads, or Pipecat. Emotion cues are lexical and
conservative; they are not presented as acoustic emotion recognition.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class SpeechProfile:
    """A restrained speech style supported by local Kokoro controls."""

    style: str
    speed: float
    conversational: bool


def _fold(text: str) -> str:
    """Case-fold and remove diacritics for robust pt-BR cue matching."""
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    folded = _fold(text)
    return any(cue in folded for cue in cues)


_DISTRESS_CUES = (
    "estou triste", "to triste", "estou mal", "to mal", "me sinto mal",
    "com medo", "tenho medo", "ansioso", "ansiosa", "desesperado",
    "desesperada", "nao aguento", "perdi alguem", "alguem morreu",
    "estou chorando", "to chorando", "me sinto sozinho", "me sinto sozinha",
)
_HURRY_CUES = (
    "estou com pressa", "to com pressa", "tenho pressa",
    "responda rapido", "responde rapido", "seja breve",
    "vai direto ao ponto", "rapidinho", "to atrasado", "estou atrasado",
    "tenho pouco tempo", "sem enrolacao", "resuma rapido", "resume rapido",
)
_EMPATHY_CUES = (
    "sinto muito", "entendo", "estou aqui", "to aqui", "vamos com calma",
    "respira", "lamento", "pode contar comigo", "nao precisa passar por isso",
)
_FOCUSED_CUES = (
    "emergencia", "perigo", "urgente", "imediatamente", "nao toque",
    "afaste-se", "afaste se", "saia do local", "risco imediato",
    "ligue para a emergencia", "procure atendimento agora",
)
_POSITIVE_CUES = (
    "parabens", "conseguiu", "deu certo", "boa noticia", "excelente",
    "incrivel", "mandou bem", "muito bom", "otimo", "orgulho de voce",
    "que conquista", "conseguimos",
)
_NEGATIVE_OUTCOME_CUES = (
    "nao consegui", "nao deu certo", "deu errado", "falhei", "reprovado",
    "reprovada", "perdi", "fracassei",
)
_CASUAL_CUES = (
    " pra ", " pro ", " ta ", " to ", " ne ", " ce ", " vc ",
    "valeu", "bora", "e ai", "kkk", "haha", "beleza", "mano",
)


def choose_speech_profile(
    user_text: str,
    reply_text: str,
    base_speed: float = 1.0,
) -> SpeechProfile:
    """Choose a restrained delivery using utterance/reply semantics.

    Priority is safety/clarity, support, celebration, then questions/default.
    Kokoro supports speed changes, not independent pitch, breath, or emotion
    controls, so the profile avoids pretending to control unsupported features.
    """
    try:
        base = float(base_speed)
    except (TypeError, ValueError):
        base = 1.0
    base = min(1.25, max(0.75, base))

    user_folded = f" {_fold(user_text)} "
    reply_folded = f" {_fold(reply_text)} "

    # A clear safety instruction should remain measured and easy to understand.
    if _contains_any(reply_text, _FOCUSED_CUES):
        style, factor = "focused", 0.97
    elif _contains_any(user_text, _HURRY_CUES):
        style, factor = "brisk", 1.08
    elif (
        _contains_any(user_text, _DISTRESS_CUES)
        or _contains_any(reply_text, _EMPATHY_CUES)
    ):
        style, factor = "gentle", 0.94
    elif (
        _contains_any(reply_text, _POSITIVE_CUES)
        or (
            _contains_any(user_text, _POSITIVE_CUES)
            and not _contains_any(user_text, _NEGATIVE_OUTCOME_CUES)
        )
    ) and not _contains_any(user_text, _NEGATIVE_OUTCOME_CUES):
        style, factor = "upbeat", 1.04
    elif reply_text.rstrip().endswith("?"):
        style, factor = "curious", 0.98
    else:
        style, factor = "calm", 1.0

    # Stay near the configured base rate: dramatic speed swings sound synthetic.
    speed = min(1.25, max(0.75, base * factor))
    cues = " " + user_folded.strip() + " " + reply_folded.strip() + " "
    conversational = style != "focused" and _contains_any(cues, _CASUAL_CUES)
    return SpeechProfile(style=style, speed=round(speed, 3), conversational=conversational)


def clean_speech_text(value: str) -> str:
    """Convert common Markdown structure into readable speech with pauses."""
    if not isinstance(value, str) or not value.strip():
        return ""

    text = re.sub(
        r"\x60{3}.*?\x60{3}", " Omiti um bloco de código da resposta. ", value, flags=re.S
    )
    # A heading or a list item is a spoken phrase boundary, not adjacent words.
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*$", r"\1.", text)
    text = re.sub(r"(?m)^\s{0,3}[-*+]\s+(.+?)\s*$", r"\1.", text)
    text = re.sub(r"(?m)^\s{0,3}\d+[.)]\s+(.+?)\s*$", r"\1.", text)
    text = re.sub(r"(?m)^\s{0,3}>\s?", "", text)
    text = re.sub(r"(?m)^\s*(?:---+|___+|\*\*\*+)\s*$", " ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\x60([^\x60]+)\x60", r"\1", text)
    text = re.sub(r"[*_~]{1,3}", "", text)
    # Decorative emoji are not usually meaningful when read aloud.
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]", " ", text)
    # Collapse layout whitespace only after headings/list boundaries gained punctuation.
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r",{2,}", ",", text)
    text = re.sub(r"([,;:])\s*([.!?])", r"\2", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if text and text[-1] not in ".!?…":
        text += "."
    return text


def prepare_spoken_reply(
    value: str,
    user_text: str = "",
    profile: SpeechProfile | None = None,
) -> str:
    """Prepare a response for speech while leaving the chat text untouched.

    Contractions are only used when either side is already conversational.
    No filler words or artificial breaths are injected automatically.
    """
    text = clean_speech_text(value)
    if not text:
        return ""
    if profile is None:
        profile = choose_speech_profile(user_text, text)

    if profile.conversational:
        # Small, reversible pt-BR contractions; safety guidance stays formal.
        substitutions = (
            (r"\bestou\b", "tô"),
            (r"\bestá\b", "tá"),
            (r"\bestão\b", "tão"),
            (r"\bestava\b", "tava"),
            (r"\bpara\b", "pra"),
        )
        for pattern, replacement in substitutions:
            text = re.sub(
                pattern,
                lambda match: replacement.capitalize()
                if match.group(0)[:1].isupper()
                else replacement,
                text,
                flags=re.IGNORECASE,
            )
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if text and text[-1] not in ".!?…":
        text += "."
    return text
