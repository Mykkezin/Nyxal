#!/usr/bin/env python3

"""
NIXAL — CONSULTA INTERNA DA AUTORREPRESENTAÇÃO

Microetapa 56.4.5

Responsabilidade:
    Permitir que outras partes internas da arquitetura consultem
    a autorrepresentação da Nixal por meio de uma interface
    estruturada e controlada.

Princípios:
1. A fonte é a autorrepresentação, não a planta diretamente.
2. A consulta não modifica a autorrepresentação.
3. A consulta não executa capacidades.
4. A consulta não inicia conversação.
5. A consulta não cria conhecimento ausente.
6. Informações não conhecidas permanecem desconhecidas.
7. Somente operações internas explicitamente declaradas são aceitas.
"""

from __future__ import annotations

from typing import Any

from nixal_autorreprentacao import AutorreprentacaoNixal


class ConsultaInternaNixal:
    """
    Porta interna de acesso ao modelo de si da Nixal.

    Esta classe não conhece a estrutura física da planta.
    Ela conhece somente a interface da autorrepresentação.
    """

    OPERACOES = {
        "identidade",
        "estado_arquitetura",
        "componentes",
        "componente",
        "funcao_componente",
        "capacidades",
        "possui_capacidade",
        "limites",
        "regras_modificacao",
        "pode_modificar",
    }

    def __init__(
        self,
        autorrepresentacao: AutorreprentacaoNixal | None = None,
    ) -> None:
        self.autorrepresentacao = (
            autorrepresentacao
            if autorrepresentacao is not None
            else AutorreprentacaoNixal()
        )

    # ============================================================
    # CONSULTA INTERNA
    # ============================================================

    def consultar(
        self,
        operacao: str,
        alvo: str | None = None,
    ) -> dict[str, Any]:
        """
        Executa somente uma consulta declarada sobre a
        autorrepresentação.

        Nenhuma operação desta classe executa capacidades.
        """

        if operacao not in self.OPERACOES:
            return self._resposta_negada(
                motivo=(
                    "Operação de consulta interna não declarada."
                )
            )

        if operacao == "identidade":
            return self.autorrepresentacao.identidade()

        if operacao == "estado_arquitetura":
            return self.autorrepresentacao.estado_arquitetura()

        if operacao == "componentes":
            return self.autorrepresentacao.componentes()

        if operacao == "capacidades":
            return self.autorrepresentacao.capacidades()

        if operacao == "limites":
            return self.autorrepresentacao.limites()

        if operacao == "regras_modificacao":
            return self.autorrepresentacao.regras_modificacao()

        if alvo is None:
            return self._resposta_negada(
                motivo=(
                    f"A operação '{operacao}' exige um alvo."
                )
            )

        if operacao == "componente":
            return self.autorrepresentacao.componente(
                alvo
            )

        if operacao == "funcao_componente":
            return self.autorrepresentacao.funcao_componente(
                alvo
            )

        if operacao == "possui_capacidade":
            return self.autorrepresentacao.possui_capacidade(
                alvo
            )

        if operacao == "pode_modificar":
            return self.autorrepresentacao.pode_modificar(
                alvo
            )

        return self._resposta_negada(
            motivo="Operação não implementada."
        )

    # ============================================================
    # ATALHOS EXPLÍCITOS
    # ============================================================

    def quem_sou(self) -> dict[str, Any]:
        return self.consultar(
            "identidade"
        )

    def quais_componentes(self) -> dict[str, Any]:
        return self.consultar(
            "componentes"
        )

    def qual_funcao_do_componente(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        return self.consultar(
            "funcao_componente",
            componente_id,
        )

    def quais_capacidades(self) -> dict[str, Any]:
        return self.consultar(
            "capacidades"
        )

    def possuo_capacidade(
        self,
        nome: str,
    ) -> dict[str, Any]:
        return self.consultar(
            "possui_capacidade",
            nome,
        )

    def quais_sao_meus_limites(self) -> dict[str, Any]:
        return self.consultar(
            "limites"
        )

    def como_posso_modificar(
        self,
        parte: str,
    ) -> dict[str, Any]:
        return self.consultar(
            "pode_modificar",
            parte,
        )

    # ============================================================
    # RESPOSTAS
    # ============================================================

    def _resposta_negada(
        self,
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "autorrepresentacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    consulta = ConsultaInternaNixal()

    print("=" * 60)
    print("NIXAL — CONSULTA INTERNA 56.4.5")
    print("=" * 60)

    print()
    print("Quem sou:")
    print(
        consulta.quem_sou()
    )

    print()
    print("Capacidades:")
    print(
        consulta.quais_capacidades()
    )

    print()
    print("Função do corpo computacional:")
    print(
        consulta.qual_funcao_do_componente(
            "corpo_computacional"
        )
    )


if __name__ == "__main__":
    main()
