#!/usr/bin/env python3

"""
NIXAL — DIÁLOGO QWEN

Microetapa 56.5.5

Responsabilidade:
    Produzir respostas livres de conversação usando o modelo Qwen.

Esta camada não seleciona nem executa capacidades.
Ela recebe somente texto + contexto recente e devolve texto.
"""

from __future__ import annotations

import os
from typing import Any

import ollama

from nixal_amd_developer_cloud import AmdCloudChatClient, AmdDeveloperCloud


class DialogoQwenNixal:
    """Adaptador conversacional do Qwen com dependência injetável."""

    FONTE = "dialogo_qwen_nixal"
    VERSAO = "56.5.5"
    MODELO_PADRAO = "qwen2:7b"

    PROMPT_SISTEMA = (
        "Você é Nyxal, uma assistente local do sistema NyxOS. "
        "Converse naturalmente em português do Brasil, seja direta, "
        "clara e útil. Não alegue ter executado ações que não foram "
        "explicitamente confirmadas pelo sistema. Nesta camada você "
        "somente conversa: não execute comandos, não altere arquivos, "
        "não altere a arquitetura e não promova conhecimento."
    )

    def __init__(
        self,
        modelo: str | None = None,
        cliente: Any = None,
    ) -> None:
        self.provedor = os.environ.get(
            "NYXAL_LLM_PROVIDER",
            "ollama",
        ).strip().lower()
        provedor_amd_cloud = self.provedor in {
            "amd_cloud",
            "amd-developer-cloud",
            "amd",
        }

        if modelo is not None:
            self.modelo = modelo
        elif provedor_amd_cloud:
            self.modelo = os.environ.get(
                "NYXAL_AMD_CLOUD_MODEL",
                AmdDeveloperCloud.MODELO_PADRAO,
            )
        else:
            self.modelo = os.environ.get(
                "NYXAL_CONVERSATIONAL_MODEL",
                self.MODELO_PADRAO,
            )

        if cliente is not None:
            self.cliente = cliente
        elif provedor_amd_cloud:
            self.cliente = AmdCloudChatClient()
        else:
            self.cliente = ollama

    def responder(
        self,
        texto: str,
        historico: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(texto, str) or not texto.strip():
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": self.FONTE,
                "resposta": None,
                "erro": "O texto conversacional é obrigatório.",
            }

        mensagens: list[dict[str, str]] = [
            {
                "role": "system",
                "content": self.PROMPT_SISTEMA,
            }
        ]

        if historico is not None:
            for item in historico:
                if not isinstance(item, dict):
                    continue

                papel = item.get("papel")
                conteudo = item.get("texto")

                if papel == "user":
                    role = "user"
                elif papel == "assistant":
                    role = "assistant"
                else:
                    continue

                if not isinstance(conteudo, str) or not conteudo.strip():
                    continue

                mensagens.append(
                    {
                        "role": role,
                        "content": conteudo,
                    }
                )

        mensagens.append(
            {
                "role": "user",
                "content": texto.strip(),
            }
        )

        try:
            resposta = self.cliente.chat(
                model=self.modelo,
                messages=mensagens,
                options={
                    "temperature": 0.4,
                },
            )
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "qwen_nao_respondeu",
                "origem": self.FONTE,
                "resposta": None,
                "erro": (
                    "Falha no diálogo Qwen: "
                    f"{type(erro).__name__}: {erro}"
                ),
            }

        if isinstance(resposta, dict):
            mensagem = resposta.get("message", {})
        else:
            mensagem = getattr(resposta, "message", {})

        if isinstance(mensagem, dict):
            conteudo = mensagem.get("content")
        else:
            conteudo = getattr(mensagem, "content", None)

        if not isinstance(conteudo, str) or not conteudo.strip():
            return {
                "sucesso": False,
                "estado": "resposta_qwen_vazia",
                "origem": self.FONTE,
                "resposta": None,
                "erro": "O Qwen não retornou texto.",
            }

        return {
            "sucesso": True,
            "estado": "resposta_gerada",
            "origem": self.FONTE,
            "resposta": conteudo.strip(),
            "modelo": self.modelo,
            "mensagens_consideradas": len(mensagens) - 1,
            "permanente": False,
            "versao_dialogo": self.VERSAO,
        }


__all__ = [
    "DialogoQwenNixal",
]
