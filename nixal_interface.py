#!/usr/bin/env python3

"""
NIXAL — INTERFACE CONVERSACIONAL

Microetapa 56.5.1

Responsabilidade:
    Definir o contrato básico da fronteira conversacional da Nixal.

Fluxo:

    usuário
        ↓
    entrada textual
        ↓
    interface conversacional
        ↓
    entrada estruturada para o núcleo

    núcleo da Nixal
        ↓
    resposta estruturada
        ↓
    interface conversacional
        ↓
    resposta textual para o usuário

Princípios:

1. A interface representa apenas a fronteira entre humano e núcleo.
2. A interface não executa capacidades.
3. A interface não modifica a arquitetura.
4. A interface não promove conhecimento permanente.
5. A interface não realiza investigação.
6. A interface não formula hipóteses.
7. A interface não executa testes.
8. A interface não avalia hipóteses.
9. A interface não acessa diretamente memória ou corpo.
10. As entradas e respostas são isoladas por cópia profunda.
11. A estrutura deve ser determinística.
12. O texto recebido não é interpretado nesta camada.
13. A interface deve distinguir entrada do usuário e resposta da Nixal.
14. Sessão e origem são metadados da comunicação, não raciocínio interno.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class InterfaceConversacionalNixal:
    """
    Define o contrato estrutural mínimo da interface conversacional.
    """

    FONTE = "interface_conversacional_nixal"

    VERSAO = "56.5.1"

    ORIGEM_USUARIO = "usuario"

    ESTADO_ENTRADA = "entrada_recebida"

    ESTADO_RESPOSTA = "resposta_pronta"

    def criar_entrada(
        self,
        texto: str,
        sessao: str | None = None,
        origem: str = ORIGEM_USUARIO,
    ) -> dict[str, Any]:
        """
        Cria uma entrada estruturada a partir de texto recebido.

        Esta operação não interpreta o conteúdo.
        """

        if not isinstance(
            texto,
            str,
        ):
            raise TypeError(
                "texto deve ser uma string"
            )

        if not texto.strip():
            raise ValueError(
                "texto não pode ser vazio"
            )

        if sessao is not None and not isinstance(
            sessao,
            str,
        ):
            raise TypeError(
                "sessao deve ser uma string ou None"
            )

        if not isinstance(
            origem,
            str,
        ):
            raise TypeError(
                "origem deve ser uma string"
            )

        texto_isolado = str(
            texto
        )

        sessao_isolada = (
            None
            if sessao is None
            else str(sessao)
        )

        origem_isolada = str(
            origem
        )

        entrada = {
            "sucesso": True,
            "estado": self.ESTADO_ENTRADA,
            "origem": self.FONTE,
            "valor": {
                "texto": texto_isolado,
                "sessao": sessao_isolada,
                "origem_mensagem": origem_isolada,
                "interpretado": False,
                "processado": False,
                "capacidade_executada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "versao_interface": self.VERSAO,
        }

        return deepcopy(
            entrada
        )

    def criar_resposta(
        self,
        texto: str,
        sessao: str | None = None,
        estado: str = ESTADO_RESPOSTA,
    ) -> dict[str, Any]:
        """
        Cria uma resposta estruturada da Nixal.

        Esta operação não interpreta nem modifica o conteúdo recebido.
        """

        if not isinstance(
            texto,
            str,
        ):
            raise TypeError(
                "texto deve ser uma string"
            )

        if not texto.strip():
            raise ValueError(
                "texto da resposta não pode ser vazio"
            )

        if sessao is not None and not isinstance(
            sessao,
            str,
        ):
            raise TypeError(
                "sessao deve ser uma string ou None"
            )

        if not isinstance(
            estado,
            str,
        ) or not estado.strip():
            raise ValueError(
                "estado deve ser uma string não vazia"
            )

        resposta = {
            "sucesso": True,
            "estado": str(
                estado
            ),
            "origem": self.FONTE,
            "resposta": str(
                texto
            ),
            "sessao": (
                None
                if sessao is None
                else str(sessao)
            ),
            "valor": {
                "texto": str(
                    texto
                ),
                "sessao": (
                    None
                    if sessao is None
                    else str(sessao)
                ),
                "interpretado": False,
                "capacidade_executada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "versao_interface": self.VERSAO,
        }

        return deepcopy(
            resposta
        )

    def validar_entrada(
        self,
        entrada: dict[str, Any],
    ) -> bool:
        """
        Valida estruturalmente uma entrada criada pela interface.
        """

        if not isinstance(
            entrada,
            dict,
        ):
            return False

        if entrada.get(
            "sucesso"
        ) is not True:
            return False

        if entrada.get(
            "estado"
        ) != self.ESTADO_ENTRADA:
            return False

        if entrada.get(
            "origem"
        ) != self.FONTE:
            return False

        if entrada.get(
            "versao_interface"
        ) != self.VERSAO:
            return False

        valor = entrada.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return False

        if not isinstance(
            valor.get("texto"),
            str,
        ):
            return False

        if not valor.get(
            "texto"
        ).strip():
            return False

        if valor.get(
            "interpretado"
        ) is not False:
            return False

        if valor.get(
            "processado"
        ) is not False:
            return False

        if valor.get(
            "capacidade_executada"
        ) is not False:
            return False

        if valor.get(
            "conhecimento_permanente"
        ) is not False:
            return False

        if valor.get(
            "arquitetura_modificada"
        ) is not False:
            return False

        return True

    def validar_resposta(
        self,
        resposta: dict[str, Any],
    ) -> bool:
        """
        Valida estruturalmente uma resposta criada pela interface.
        """

        if not isinstance(
            resposta,
            dict,
        ):
            return False

        if resposta.get(
            "sucesso"
        ) is not True:
            return False

        if resposta.get(
            "origem"
        ) != self.FONTE:
            return False

        if resposta.get(
            "versao_interface"
        ) != self.VERSAO:
            return False

        estado = resposta.get(
            "estado"
        )

        if not isinstance(
            estado,
            str,
        ) or not estado.strip():
            return False

        texto = resposta.get(
            "resposta"
        )

        if not isinstance(
            texto,
            str,
        ) or not texto.strip():
            return False

        valor = resposta.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return False

        if valor.get(
            "texto"
        ) != texto:
            return False

        if valor.get(
            "interpretado"
        ) is not False:
            return False

        if valor.get(
            "capacidade_executada"
        ) is not False:
            return False

        if valor.get(
            "conhecimento_permanente"
        ) is not False:
            return False

        if valor.get(
            "arquitetura_modificada"
        ) is not False:
            return False

        return True

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não executa capacidades"
        )

    def interpretar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não interpreta mensagens"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não promove conhecimento permanente"
        )

    def investigar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não realiza investigação"
        )

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não formula hipóteses"
        )

    def executar_teste(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não executa testes"
        )

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "InterfaceConversacionalNixal não avalia hipóteses"
        )


__all__ = [
    "InterfaceConversacionalNixal",
]
