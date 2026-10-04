#!/usr/bin/env python3

"""
NIXAL — CONVERSA LOCAL POR TERMINAL

Microetapa 56.5.5

Usa a mesma cadeia conversacional da API:
    sessão
      ↓
    transporte
      ↓
    núcleo conversacional
      ↓
    memória contextual volátil + Qwen

O histórico é perdido quando este processo termina.
"""

from __future__ import annotations

from nixal_integracao_sessao_transporte import (
    IntegracaoSessaoTransporteNixal,
)
from nixal_nucleo_conversacional import (
    NucleoConversacionalNixal,
)
from nixal_transporte_conversacional import (
    TransporteConversacionalNixal,
)


def extrair_resposta(resultado: dict) -> str:
    if not isinstance(resultado, dict):
        return "A Nyxal retornou uma estrutura inválida."

    valor = resultado.get("valor")

    if isinstance(valor, dict):
        transporte = valor.get("transporte")

        if isinstance(transporte, dict):
            resposta = transporte.get("resposta")

            if isinstance(resposta, dict):
                texto = resposta.get("resposta")

                if isinstance(texto, str) and texto.strip():
                    return texto

    erro = resultado.get("erro")

    if isinstance(erro, str) and erro.strip():
        return erro

    return "A Nyxal não conseguiu gerar uma resposta."


def main() -> None:
    nucleo = NucleoConversacionalNixal()
    transporte = TransporteConversacionalNixal()
    integracao = IntegracaoSessaoTransporteNixal(
        transporte=transporte,
    )

    sessao_id: str | None = None

    print("=" * 64)
    print("NYXAL — CONVERSA LOCAL")
    print("=" * 64)
    print("Digite sua mensagem.")
    print("Digite 'sair' para encerrar.")
    print()

    while True:
        try:
            texto = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not texto:
            continue

        if texto.casefold() in {"sair", "exit", "quit"}:
            break

        resultado = integracao.processar_mensagem(
            texto=texto,
            nucleo=nucleo,
            sessao_id=sessao_id,
        )

        if sessao_id is None:
            possivel_sessao = resultado.get("sessao")

            if isinstance(possivel_sessao, str):
                sessao_id = possivel_sessao

        resposta = extrair_resposta(resultado)

        print(f"Nyxal: {resposta}")
        print()

        if resultado.get("sucesso") is not True:
            print(
                f"[estado: {resultado.get('estado', 'desconhecido')}]"
            )
            print()

    if sessao_id is not None:
        integracao.encerrar_sessao(sessao_id)

    print("Conversa encerrada.")


if __name__ == "__main__":
    main()
