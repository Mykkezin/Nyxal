#!/usr/bin/env python3

"""
NIXAL — TESTE DO ADAPTADOR DIALOGO QWEN

Microetapa 56.5.5

Valida o contrato de leitura da resposta do cliente Ollama em dois formatos:
    - objeto ChatResponse com atributo .message.content
    - dicionário compatível com response["message"]["content"]

Nenhum servidor Ollama ou modelo real é consultado.
"""

from __future__ import annotations

import sys
import types


class ClienteFake:
    def __init__(self, resposta) -> None:
        self.resposta = resposta
        self.chamada = None

    def chat(self, **kwargs):
        self.chamada = kwargs
        return self.resposta


chat_response_fake = types.SimpleNamespace(
    message=types.SimpleNamespace(
        content="Resposta vinda de ChatResponse."
    )
)

ollama_fake = types.ModuleType("ollama")
ollama_fake.chat = lambda **_kwargs: chat_response_fake

sys.modules["ollama"] = ollama_fake

from nixal_dialogo_qwen import DialogoQwenNixal


def verificar(condicao: bool, mensagem: str, falhas: list[str], total: list[int]) -> None:
    total[0] += 1
    print(
        f"[{'PASS' if condicao else 'FAIL'}] "
        f"{total[0]}. {mensagem}"
    )
    if not condicao:
        falhas.append(mensagem)


def main() -> None:
    falhas: list[str] = []
    total = [0]

    cliente_objeto = ClienteFake(chat_response_fake)
    dialogo_objeto = DialogoQwenNixal(
        modelo="qwen2:7b",
        cliente=cliente_objeto,
    )

    resultado_objeto = dialogo_objeto.responder(
        "Olá Nyxal.",
        historico=[
            {"papel": "user", "texto": "Antes."},
            {"papel": "assistant", "texto": "Resposta anterior."},
        ],
    )

    verificar(
        resultado_objeto["sucesso"] is True,
        "ChatResponse com .message.content é aceito",
        falhas,
        total,
    )

    verificar(
        resultado_objeto["resposta"] == "Resposta vinda de ChatResponse.",
        "conteúdo do ChatResponse é extraído corretamente",
        falhas,
        total,
    )

    verificar(
        cliente_objeto.chamada["model"] == "qwen2:7b",
        "modelo configurado é enviado ao cliente",
        falhas,
        total,
    )

    verificar(
        len(cliente_objeto.chamada["messages"]) == 4,
        "mensagens de sistema, histórico e turno atual são enviadas",
        falhas,
        total,
    )

    cliente_dicionario = ClienteFake(
        {
            "message": {
                "content": "Resposta em formato dicionário."
            }
        }
    )

    dialogo_dicionario = DialogoQwenNixal(
        modelo="qwen2:7b",
        cliente=cliente_dicionario,
    )

    resultado_dicionario = dialogo_dicionario.responder(
        "Teste dicionário."
    )

    verificar(
        resultado_dicionario["sucesso"] is True,
        "formato dicionário continua sendo aceito",
        falhas,
        total,
    )

    verificar(
        resultado_dicionario["resposta"] == "Resposta em formato dicionário.",
        "conteúdo do dicionário continua sendo extraído corretamente",
        falhas,
        total,
    )

    print()
    print("=" * 64)
    print("TESTE — ADAPTADOR DIALOGO QWEN 56.5.5")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {total[0]}")
    print(f"FALHAS: {len(falhas)}")
    print(f"PASSOU: {not falhas}")
    print("=" * 64)

    if falhas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
