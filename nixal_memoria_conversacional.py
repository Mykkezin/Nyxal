#!/usr/bin/env python3

"""
NIXAL — MEMÓRIA CONVERSACIONAL EFÊMERA

Microetapa 56.5.5

Responsabilidade:
    Manter o contexto recente de uma sessão conversacional enquanto
    o processo da Nyxal estiver em execução.

Esta camada NÃO:
    - promove conhecimento permanente;
    - altera arquitetura;
    - acessa o corpo;
    - executa capacidades;
    - investiga;
    - formula hipóteses;
    - persiste mensagens em arquivo;
    - substitui a memória de conhecimento.

O conteúdo é volátil: reiniciar o processo elimina o histórico.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class MemoriaConversacionalNixal:
    """Armazena somente o contexto recente e volátil de conversas."""

    ORIGEM = "memoria_conversacional_nixal"
    VERSAO = "56.5.5"
    PADRAO_MAX_MENSAGENS = 12

    def __init__(
        self,
        max_mensagens: int = PADRAO_MAX_MENSAGENS,
    ) -> None:
        if not isinstance(max_mensagens, int) or max_mensagens <= 0:
            raise ValueError(
                "max_mensagens precisa ser um inteiro positivo."
            )

        self.max_mensagens = max_mensagens
        self._historicos: dict[str, list[dict[str, str]]] = {}

    def registrar(
        self,
        sessao: str,
        papel: str,
        texto: str,
    ) -> dict[str, Any]:
        sessao_normalizada = self._normalizar_sessao(sessao)
        papel_normalizado = self._normalizar_papel(papel)

        if sessao_normalizada is None:
            return self._erro("Sessão inválida.")

        if papel_normalizado is None:
            return self._erro("Papel inválido.")

        if not isinstance(texto, str) or not texto.strip():
            return self._erro("Texto inválido.")

        historico = self._historicos.setdefault(
            sessao_normalizada,
            [],
        )

        historico.append(
            {
                "papel": papel_normalizado,
                "texto": texto.strip(),
            }
        )

        excesso = max(
            len(historico) - self.max_mensagens,
            0,
        )

        if excesso:
            del historico[:excesso]

        return {
            "sucesso": True,
            "estado": "mensagem_registrada",
            "origem": self.ORIGEM,
            "sessao": sessao_normalizada,
            "quantidade": len(historico),
            "valor": deepcopy(historico[-1]),
            "permanente": False,
            "versao_memoria": self.VERSAO,
        }

    def obter(
        self,
        sessao: str,
        limite: int | None = None,
    ) -> dict[str, Any]:
        sessao_normalizada = self._normalizar_sessao(sessao)

        if sessao_normalizada is None:
            return self._erro("Sessão inválida.")

        if limite is not None:
            if not isinstance(limite, int) or limite <= 0:
                return self._erro("limite precisa ser um inteiro positivo.")

        historico = self._historicos.get(
            sessao_normalizada,
            [],
        )

        if limite is not None:
            historico = historico[-limite:]

        return {
            "sucesso": True,
            "estado": "contexto_obtido",
            "origem": self.ORIGEM,
            "sessao": sessao_normalizada,
            "quantidade": len(historico),
            "mensagens": deepcopy(historico),
            "permanente": False,
            "versao_memoria": self.VERSAO,
        }

    def limpar(
        self,
        sessao: str,
    ) -> dict[str, Any]:
        sessao_normalizada = self._normalizar_sessao(sessao)

        if sessao_normalizada is None:
            return self._erro("Sessão inválida.")

        removido = self._historicos.pop(
            sessao_normalizada,
            None,
        )

        return {
            "sucesso": True,
            "estado": (
                "contexto_limpo"
                if removido is not None
                else "contexto_ja_vazio"
            ),
            "origem": self.ORIGEM,
            "sessao": sessao_normalizada,
            "quantidade_removida": (
                len(removido)
                if removido is not None
                else 0
            ),
            "permanente": False,
            "versao_memoria": self.VERSAO,
        }

    def possui_sessao(
        self,
        sessao: str,
    ) -> bool:
        sessao_normalizada = self._normalizar_sessao(sessao)
        if sessao_normalizada is None:
            return False
        return sessao_normalizada in self._historicos

    def _erro(
        self,
        mensagem: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "operacao_negada",
            "origem": self.ORIGEM,
            "erro": mensagem,
            "permanente": False,
            "versao_memoria": self.VERSAO,
        }

    @staticmethod
    def _normalizar_sessao(
        sessao: str,
    ) -> str | None:
        if not isinstance(sessao, str):
            return None
        valor = sessao.strip()
        return valor or None

    @staticmethod
    def _normalizar_papel(
        papel: str,
    ) -> str | None:
        if not isinstance(papel, str):
            return None

        valor = papel.strip().lower()

        if valor not in {"user", "assistant"}:
            return None

        return valor


__all__ = [
    "MemoriaConversacionalNixal",
]
