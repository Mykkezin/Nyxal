#!/usr/bin/env python3
"""Classificação simples de intenção e telemetria privada do roteador Nyxal."""
from __future__ import annotations

import threading
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any


PREFERENCES: dict[str, tuple[str, ...]] = {
    "memoria_continuidade": ("letta", "openai", "gemini", "grok", "hermes"),
    "ferramentas_e_operacao": ("hermes", "openai", "gemini", "grok", "letta"),
    "ciencia_dados": ("openai", "hermes", "gemini", "grok", "letta"),
    "codigo_e_raciocinio": ("openai", "hermes", "gemini", "grok", "letta"),
    "engenharia_reversa": ("hermes", "openai", "gemini", "grok", "letta"),
    "ciberseguranca_defensiva": ("hermes", "openai", "gemini", "grok", "letta"),
    "conhecimento_geral": ("openai", "gemini", "grok", "hermes", "letta"),
}


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def classificar_intencao(mensagem: str) -> dict[str, str]:
    """Classifica por marcadores de intenção; não grava a mensagem."""
    text = _fold(mensagem)
    memory_markers = (
        "me lembra", "me lembre", "lembra o que", "lembre o que",
        "conversa anterior", "conversas anteriores", "historico da conversa",
        "o que combinamos", "como combinamos", "o que eu pedi antes",
        "o que eu disse antes", "continue de onde paramos",
        "retome de onde paramos", "decisao anterior",
    )
    if any(marker in text for marker in memory_markers):
        return {
            "classe": "memoria_continuidade",
            "motivo": "O pedido depende de recuperar uma conversa ou decisão anterior.",
        }

    reverse_markers = (
        "engenharia reversa", "reverse engineering", "reverse engineer",
        "reconstruir a arquitetura", "mapear dependencias", "mapear dependências",
        "analisar um binario", "analisar um binário", "descompilar",
        "reconstruir protocolo", "investigar formato de arquivo",
        "entender como esse software funciona", "analisar comportamento do programa",
        "engenharia inversa",
    )
    if any(marker in text for marker in reverse_markers):
        return {
            "classe": "engenharia_reversa",
            "motivo": "O pedido indica análise estrutural de um artefato autorizado.",
        }

    cyber_markers = (
        "ciberseguranca defensiva", "cybersecurity defensiva",
        "hardening de seguranca", "triagem de vulnerabilidades",
        "modelagem de ameacas", "analise defensiva de logs",
    )
    if any(marker in text for marker in cyber_markers):
        return {
            "classe": "ciberseguranca_defensiva",
            "motivo": "O pedido é orientado à defesa de ativos autorizados.",
        }

    tool_markers = (
        "execute", "executar", "rode ", "rodar ", "instale", "instalar",
        "deploy", "pull request", "merge", "branch", "github", "vps",
        "systemctl", "docker", "terminal", "comando shell", "altere o arquivo",
        "edite o arquivo", "modifique o arquivo", "corrija o codigo",
        "implemente", "aplique a correcao", "audite meu repositorio",
        "analise meu repositorio", "revise este repositorio", "escaneie",
        "teste meu codigo", "execute os testes", "crie um arquivo",
        "cybersecurity defensiva", "ciberseguranca defensiva",
    )
    if any(marker in text for marker in tool_markers):
        return {
            "classe": "ferramentas_e_operacao",
            "motivo": "O pedido sugere trabalho sobre código, infraestrutura ou ferramentas.",
        }

    data_markers = (
        "data science", "datascience", "dataset", "analise exploratoria",
        "analise de dados", "analise estatistica", "regressao", "machine learning",
        "treine um modelo", "treinar modelo", "notebook python", "consulta sql",
        "visualize os dados", "grafico dos dados", "experimento",
    )
    if any(marker in text for marker in data_markers):
        return {
            "classe": "ciencia_dados",
            "motivo": "O pedido envolve análise de dados, estatística ou modelagem.",
        }

    code_markers = (
        "escreva codigo", "escreve codigo", "programa em ", "debug", "depure",
        "erro de compilacao", "refatore", "refatorar", "teste unitario",
        "revisao de codigo", "code review", "arquitetura de software",
    )
    if any(marker in text for marker in code_markers):
        return {
            "classe": "codigo_e_raciocinio",
            "motivo": "O pedido envolve programação ou raciocínio técnico.",
        }
    return {
        "classe": "conhecimento_geral",
        "motivo": "Sem uma intenção especializada detectada; prioriza um modelo de uso geral.",
    }


def ordem_provedores(classe: str) -> tuple[str, ...]:
    return PREFERENCES.get(classe, PREFERENCES["conhecimento_geral"])


class TelemetriaRoteador:
    """Mantém os últimos 100 eventos sem prompt ou conteúdo de resposta."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def registrar(
        self,
        *,
        classe: str,
        provedor: str,
        sucesso: bool,
        inicio: float,
        tentativas: list[str],
        erro: str | None = None,
        fallback_local: bool = False,
    ) -> None:
        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "classe": classe,
            "provedor": provedor,
            "sucesso": bool(sucesso),
            "latencia_ms": round((time.monotonic() - inicio) * 1000),
            "tentativas": list(tentativas),
        }
        if erro:
            event["erro"] = erro
        if fallback_local:
            event["fallback_local"] = True
        with self._lock:
            self._events.append(event)
            if len(self._events) > 100:
                del self._events[:-100]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            events = [dict(event) for event in self._events]
        by_class: dict[str, int] = {}
        by_provider: dict[str, int] = {}
        latencies: list[int] = []
        successes = 0
        for event in events:
            label = str(event.get("classe") or "desconhecida")
            provider = str(event.get("provedor") or "desconhecido")
            by_class[label] = by_class.get(label, 0) + 1
            by_provider[provider] = by_provider.get(provider, 0) + 1
            successes += int(event.get("sucesso") is True)
            latency = event.get("latencia_ms")
            if isinstance(latency, int) and latency >= 0:
                latencies.append(latency)
        return {
            "politica": "roteamento_por_intencao_v1",
            "retencao": "ultimos_100_eventos_em_memoria; sem_prompt_ou_resposta",
            "eventos_em_memoria": len(events),
            "taxa_sucesso_percentual": round(successes / len(events) * 100, 1) if events else None,
            "latencia_media_ms": round(sum(latencies) / len(latencies)) if latencies else None,
            "classes": by_class,
            "provedores": by_provider,
            "ultimos_eventos": events[-5:][::-1],
        }
