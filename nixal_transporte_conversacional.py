#!/usr/bin/env python3

"""
NIXAL — TRANSPORTE CONVERSACIONAL

Microetapa 56.5.2

Responsabilidade:
    Fazer a ponte entre a interface conversacional e o núcleo da Nixal.

Fluxo:

    usuário
        ↓
    InterfaceConversacionalNixal
        ↓
    entrada estruturada
        ↓
    TransporteConversacionalNixal
        ↓
    núcleo
        ↓
    resposta estruturada
        ↓
    TransporteConversacionalNixal
        ↓
    InterfaceConversacionalNixal
        ↓
    usuário

Princípios:

1. O transporte não interpreta linguagem natural.
2. O transporte não executa capacidades.
3. O transporte não acessa memória.
4. O transporte não acessa o corpo.
5. O transporte não investiga.
6. O transporte não formula hipóteses.
7. O transporte não executa testes.
8. O transporte não avalia hipóteses.
9. O transporte não modifica a arquitetura.
10. O transporte não promove conhecimento permanente.
11. O núcleo é uma dependência externa injetada.
12. A entrada enviada ao núcleo deve ser uma cópia isolada.
13. A resposta recebida do núcleo deve ser validada pela interface.
14. A saída do transporte preserva entrada e resposta para rastreabilidade.
15. A camada deve permanecer determinística quando o núcleo também for determinístico.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_interface import (
    InterfaceConversacionalNixal,
)


class TransporteConversacionalNixal:
    """
    Faz o transporte entre a interface conversacional e o núcleo.
    """

    FONTE = "transporte_conversacional_nixal"

    ESTADO_PROCESSADO = "mensagem_processada"

    def __init__(
        self,
        interface: InterfaceConversacionalNixal | None = None,
    ) -> None:
        if interface is not None and not isinstance(
            interface,
            InterfaceConversacionalNixal,
        ):
            raise TypeError(
                "interface deve ser uma instância de "
                "InterfaceConversacionalNixal"
            )

        self._interface = (
            interface
            if interface is not None
            else InterfaceConversacionalNixal()
        )

    def processar_mensagem(
        self,
        texto: str,
        nucleo: Any,
        sessao: str | None = None,
    ) -> dict[str, Any]:
        """
        Recebe uma mensagem humana, encaminha ao núcleo e retorna
        a resposta estruturada produzida pelo núcleo.

        A interpretação permanece responsabilidade do núcleo.
        """

        if not hasattr(
            nucleo,
            "processar",
        ) or not callable(
            nucleo.processar
        ):
            return self._negado(
                "O núcleo precisa fornecer um método executável "
                "chamado 'processar'."
            )

        try:
            entrada = self._interface.criar_entrada(
                texto=texto,
                sessao=sessao,
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            return self._negado(
                str(exc)
            )

        if not self._interface.validar_entrada(
            entrada
        ):
            return self._negado(
                "A interface produziu uma entrada estruturalmente inválida."
            )

        entrada_para_nucleo = deepcopy(
            entrada
        )

        try:
            resposta_nucleo = nucleo.processar(
                entrada_para_nucleo
            )
        except Exception as exc:
            return {
                "sucesso": False,
                "estado": "nucleo_nao_respondeu",
                "origem": self.FONTE,
                "valor": {
                    "entrada": deepcopy(
                        entrada
                    ),
                    "resposta": None,
                    "mensagem_processada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O núcleo lançou uma exceção durante o processamento: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }

        if not isinstance(
            resposta_nucleo,
            dict,
        ):
            return self._negado(
                "O núcleo retornou uma resposta inválida."
            )

        resposta_isolada = deepcopy(
            resposta_nucleo
        )

        if not self._interface.validar_resposta(
            resposta_isolada
        ):
            return {
                "sucesso": False,
                "estado": "resposta_nucleo_invalida",
                "origem": self.FONTE,
                "valor": {
                    "entrada": deepcopy(
                        entrada
                    ),
                    "resposta": deepcopy(
                        resposta_nucleo
                    ),
                    "mensagem_processada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O núcleo retornou uma estrutura que não atende "
                    "ao contrato da interface conversacional."
                ),
            }

        return {
            "sucesso": True,
            "estado": self.ESTADO_PROCESSADO,
            "origem": self.FONTE,
            "valor": {
                "entrada": deepcopy(
                    entrada
                ),
                "resposta": deepcopy(
                    resposta_isolada
                ),
                "mensagem_processada": True,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "resposta": deepcopy(
                resposta_isolada
            ),
        }

    def enviar_entrada(
        self,
        entrada: dict[str, Any],
        nucleo: Any,
    ) -> dict[str, Any]:
        """
        Encaminha diretamente uma entrada já estruturada.

        Esta operação é útil para futuras camadas internas que já
        tenham produzido o contrato da 56.5.1.
        """

        if not isinstance(
            entrada,
            dict,
        ):
            return self._negado(
                "Entrada precisa ser um dicionário."
            )

        if not self._interface.validar_entrada(
            entrada
        ):
            return self._negado(
                "A entrada não atende ao contrato da interface."
            )

        if not hasattr(
            nucleo,
            "processar",
        ) or not callable(
            nucleo.processar
        ):
            return self._negado(
                "O núcleo precisa fornecer um método executável "
                "chamado 'processar'."
            )

        entrada_original = deepcopy(
            entrada
        )

        try:
            resposta_nucleo = nucleo.processar(
                deepcopy(
                    entrada_original
                )
            )
        except Exception as exc:
            return {
                "sucesso": False,
                "estado": "nucleo_nao_respondeu",
                "origem": self.FONTE,
                "valor": {
                    "entrada": deepcopy(
                        entrada_original
                    ),
                    "resposta": None,
                    "mensagem_processada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O núcleo lançou uma exceção durante o processamento: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }

        if not isinstance(
            resposta_nucleo,
            dict,
        ):
            return self._negado(
                "O núcleo retornou uma resposta inválida."
            )

        resposta_isolada = deepcopy(
            resposta_nucleo
        )

        if not self._interface.validar_resposta(
            resposta_isolada
        ):
            return {
                "sucesso": False,
                "estado": "resposta_nucleo_invalida",
                "origem": self.FONTE,
                "valor": {
                    "entrada": deepcopy(
                        entrada_original
                    ),
                    "resposta": deepcopy(
                        resposta_nucleo
                    ),
                    "mensagem_processada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O núcleo retornou uma estrutura que não atende "
                    "ao contrato da interface conversacional."
                ),
            }

        return {
            "sucesso": True,
            "estado": self.ESTADO_PROCESSADO,
            "origem": self.FONTE,
            "valor": {
                "entrada": deepcopy(
                    entrada_original
                ),
                "resposta": deepcopy(
                    resposta_isolada
                ),
                "mensagem_processada": True,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "resposta": deepcopy(
                resposta_isolada
            ),
        }

    def interpretar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não interpreta mensagens"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não executa capacidades"
        )

    def acessar_memoria(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não acessa memória"
        )

    def acessar_corpo(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não acessa o corpo"
        )

    def investigar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não realiza investigação"
        )

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não formula hipóteses"
        )

    def executar_teste(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não executa testes"
        )

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não avalia hipóteses"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não promove conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "TransporteConversacionalNixal não modifica a arquitetura"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "transporte_conversacional_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "TransporteConversacionalNixal",
]
