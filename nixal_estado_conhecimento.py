#!/usr/bin/env python3

"""
NIXAL — ESTADO DE CONHECIMENTO DA AUTORREPRESENTAÇÃO

Microetapa 56.4.6

Responsabilidade:
    Representar explicitamente o estado do conhecimento da Nixal
    sobre si mesma.

Estados:

    conhecido
        Informação declarada explicitamente e encontrada.

    nao_declarado
        O tipo de informação é conhecido pela arquitetura, mas o
        alvo consultado não está declarado na planta.

    desconhecido
        Não há informação suficiente, ou a consulta não possui uma
        interpretação formal nesta camada.

Princípios:
1. Não confundir ausência de declaração com conhecimento negativo.
2. Não transformar "não declarado" em "não existe".
3. Não inventar informações.
4. Usar a autorrepresentação como única fonte.
5. Não acessar a planta diretamente.
6. Não executar capacidades.
7. Manter a camada somente de leitura.
"""

from __future__ import annotations

from typing import Any

from nixal_consulta_interna import ConsultaInternaNixal


ESTADO_CONHECIDO = "conhecido"
ESTADO_NAO_DECLARADO = "nao_declarado"
ESTADO_DESCONHECIDO = "desconhecido"


class EstadoConhecimentoNixal:
    """
    Camada responsável apenas pela classificação epistemológica
    das respostas da autorrepresentação.

    Ela não descobre novos fatos.
    Apenas classifica o que a autorrepresentação permite afirmar.
    """

    def __init__(
        self,
        consulta_interna: ConsultaInternaNixal | None = None,
    ) -> None:
        self.consulta = (
            consulta_interna
            if consulta_interna is not None
            else ConsultaInternaNixal()
        )

    # ============================================================
    # CAPACIDADES
    # ============================================================

    def capacidade(
        self,
        nome: str,
    ) -> dict[str, Any]:
        capacidades = self.consulta.quais_capacidades()

        if capacidades.get("estado") != ESTADO_CONHECIDO:
            return self._desconhecido(
                "A lista de capacidades não está conhecida."
            )

        valores = capacidades.get("valor")

        if not isinstance(valores, list):
            return self._desconhecido(
                "A estrutura das capacidades não é conhecida."
            )

        if nome in valores:
            return self._conhecido(
                valor=True,
                tipo="capacidade",
                alvo=nome,
            )

        return self._nao_declarado(
            tipo="capacidade",
            alvo=nome,
        )

    # ============================================================
    # COMPONENTES
    # ============================================================

    def componente(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        resposta = self.consulta.consultar(
            "componente",
            componente_id,
        )

        if resposta.get("estado") == ESTADO_CONHECIDO:
            return self._conhecido(
                valor=resposta.get("valor"),
                tipo="componente",
                alvo=componente_id,
            )

        if resposta.get("estado") == ESTADO_DESCONHECIDO:
            return self._nao_declarado(
                tipo="componente",
                alvo=componente_id,
            )

        return self._desconhecido(
            "Não foi possível classificar o componente."
        )

    # ============================================================
    # FUNÇÃO DE COMPONENTE
    # ============================================================

    def funcao_componente(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        componente = self.componente(
            componente_id
        )

        if componente.get("estado") == ESTADO_NAO_DECLARADO:
            return componente

        if componente.get("estado") != ESTADO_CONHECIDO:
            return componente

        valor = componente.get("valor")

        if not isinstance(valor, dict):
            return self._desconhecido(
                "A estrutura do componente não está disponível."
            )

        funcao = valor.get("funcao")

        if isinstance(funcao, str) and funcao.strip():
            return self._conhecido(
                valor=funcao,
                tipo="funcao_componente",
                alvo=componente_id,
            )

        return self._desconhecido(
            "A função do componente não está declarada."
        )

    # ============================================================
    # CONSULTA FORMAL
    # ============================================================

    def classificar_resposta(
        self,
        resposta: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Classifica uma resposta já obtida da autorrepresentação.

        Esta função nunca altera o conteúdo factual da resposta.
        """

        if not isinstance(resposta, dict):
            return self._desconhecido(
                "Resposta inválida."
            )

        estado = resposta.get("estado")

        if estado == ESTADO_CONHECIDO:
            return {
                "sucesso": True,
                "estado": ESTADO_CONHECIDO,
                "origem": "estado_conhecimento_nixal",
                "valor": resposta.get("valor"),
            }

        if estado == ESTADO_DESCONHECIDO:
            return {
                "sucesso": True,
                "estado": ESTADO_DESCONHECIDO,
                "origem": "estado_conhecimento_nixal",
                "valor": None,
            }

        if estado == "negado":
            return {
                "sucesso": True,
                "estado": ESTADO_DESCONHECIDO,
                "origem": "estado_conhecimento_nixal",
                "valor": None,
            }

        return self._desconhecido(
            "Estado de resposta não reconhecido."
        )

    # ============================================================
    # RESPOSTAS
    # ============================================================

    @staticmethod
    def _conhecido(
        valor: Any,
        tipo: str,
        alvo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": ESTADO_CONHECIDO,
            "origem": "estado_conhecimento_nixal",
            "tipo": tipo,
            "alvo": alvo,
            "valor": valor,
        }

    @staticmethod
    def _nao_declarado(
        tipo: str,
        alvo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": ESTADO_NAO_DECLARADO,
            "origem": "estado_conhecimento_nixal",
            "tipo": tipo,
            "alvo": alvo,
            "valor": None,
        }

    @staticmethod
    def _desconhecido(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": ESTADO_DESCONHECIDO,
            "origem": "estado_conhecimento_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    estado = EstadoConhecimentoNixal()

    print("=" * 60)
    print("NIXAL — ESTADO DE CONHECIMENTO 56.4.6")
    print("=" * 60)

    print()
    print("Capacidade conhecida:")
    print(
        estado.capacidade("ler_estado_corpo")
    )

    print()
    print("Capacidade não declarada:")
    print(
        estado.capacidade("camera")
    )

    print()
    print("Componente conhecido:")
    print(
        estado.componente("corpo_computacional")
    )

    print()
    print("Componente não declarado:")
    print(
        estado.componente("camera")
    )


if __name__ == "__main__":
    main()
