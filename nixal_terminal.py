#!/usr/bin/env python3

from __future__ import annotations

from nixal_interface import InterfaceConversacionalNixal
from nixal_transporte_conversacional import TransporteConversacionalNixal
from nixal_integracao_sessao_transporte import (
    IntegracaoSessaoTransporteNixal,
)
from nixal_nucleo_conversacional import NucleoConversacionalNixal


def main() -> None:

    interface = InterfaceConversacionalNixal()

    transporte = TransporteConversacionalNixal(
        interface
    )

    integracao = IntegracaoSessaoTransporteNixal(
        transporte
    )

    nucleo = NucleoConversacionalNixal(
        interface=interface
    )

    sessao_id = None

    print("=" * 60)
    print("NIXAL — INTERFACE CONVERSACIONAL")
    print("=" * 60)
    print("Digite uma mensagem.")
    print("Use Ctrl+C ou Ctrl+D para encerrar.")
    print("=" * 60)

    while True:

        try:

            texto = input("\nVocê: ")

        except (KeyboardInterrupt, EOFError):

            print("\n\nNixal encerrada.")
            break

        texto = texto.strip()

        if not texto:
            continue

        resultado = integracao.processar_mensagem(
            texto=texto,
            nucleo=nucleo,
            sessao_id=sessao_id,
        )

        if not resultado.get("sucesso"):

            print(
                "\nNixal: "
                + str(
                    resultado.get(
                        "erro",
                        "Não foi possível processar a mensagem.",
                    )
                )
            )

            continue

        sessao_id = resultado.get(
            "sessao"
        )

        resposta = (
            resultado
            .get("valor", {})
            .get("transporte", {})
            .get("resposta", {})
        )

        texto_resposta = (
            resposta
            .get("resposta")
            if isinstance(resposta, dict)
            else None
        )

        if not isinstance(
            texto_resposta,
            str,
        ):

            print(
                "\nNixal: "
                "A resposta recebida não possui texto válido."
            )

            continue

        print(
            "\nNixal: "
            + texto_resposta
        )


if __name__ == "__main__":
    main()
