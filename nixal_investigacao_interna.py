#!/usr/bin/env python3

"""
NIXAL — INVESTIGAÇÃO INTERNA

Microetapa 56.4.11

Responsabilidade:
    Executar uma investigação interna controlada usando apenas
    capacidades já declaradas e produzir evidências estruturadas.

Esta camada ainda não formula hipóteses nem transforma evidência
em conhecimento permanente.

Princípios:
1. A pergunta vem da formulação de investigação.
2. Fontes precisam ser capacidades já declaradas.
3. Execução é explícita e limitada às fontes autorizadas.
4. Resultados são tratados como evidências da investigação.
5. A investigação não altera a planta ou a arquitetura.
6. Evidência não é automaticamente verdade permanente.
7. Não há hipóteses nesta camada.
"""

from __future__ import annotations

from typing import Any

from nixal_autorreprentacao import AutorreprentacaoNixal
from nixal_capacidades import GerenciadorCapacidades


FONTES_PERMITIDAS = {
    "listar_arquivos",
    "ler_arquivo",
    "obter_hora",
    "ler_estado_corpo",
    "ler_memoria_corporal",
}

MAX_EVIDENCIA_CHARS = 4000


class InvestigacaoInternaNixal:
    """
    Investigador interno controlado.

    O investigador conhece apenas a interface do gerenciador de
    capacidades e a autorrepresentação para selecionar alvos
    explicitamente declarados.
    """

    FONTE = "investigacao_interna_nixal"

    def __init__(
        self,
        gerenciador: GerenciadorCapacidades | None = None,
        autorrepresentacao: AutorreprentacaoNixal | None = None,
    ) -> None:
        self.gerenciador = (
            gerenciador
            if gerenciador is not None
            else GerenciadorCapacidades()
        )

        self.autorrepresentacao = (
            autorrepresentacao
            if autorrepresentacao is not None
            else AutorreprentacaoNixal()
        )

    # ============================================================
    # INVESTIGAÇÃO
    # ============================================================

    def executar(
        self,
        investigacao: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            investigacao,
            dict,
        ):
            return self._negado(
                "Investigação inválida."
            )

        pergunta = investigacao.get(
            "pergunta"
        )

        tipo = investigacao.get(
            "tipo_investigacao"
        )

        if not isinstance(
            pergunta,
            str,
        ) or not pergunta.strip():
            return self._negado(
                "A investigação precisa de uma pergunta."
            )

        fontes = self._selecionar_fontes(
            tipo
        )

        evidencias: list[dict[str, Any]] = []

        for fonte in fontes:
            if fonte not in FONTES_PERMITIDAS:
                return self._negado(
                    f"Fonte não permitida: {fonte}"
                )

            if fonte == "listar_arquivos":
                evidencias.append(
                    self._executar_fonte(
                        fonte
                    )
                )

            elif fonte == "ler_arquivo":
                evidencias.extend(
                    self._investigar_arquivos()
                )

            else:
                evidencias.append(
                    self._executar_fonte(
                        fonte
                    )
                )

        return {
            "sucesso": True,
            "estado": (
                "evidencia_coletada"
                if evidencias
                else "sem_evidencia"
            ),
            "origem": self.FONTE,
            "valor": {
                "pergunta": pergunta,
                "tipo_investigacao": tipo,
                "fontes_utilizadas": fontes,
                "evidencias": evidencias,
                "conclusao": None,
                "hipotese": None,
            },
        }

    # ============================================================
    # SELEÇÃO DE FONTES
    # ============================================================

    @staticmethod
    def _selecionar_fontes(
        tipo: Any,
    ) -> list[str]:
        if tipo == "mapeamento_arquitetural":
            return [
                "listar_arquivos",
                "ler_arquivo",
            ]

        if tipo == "identidade":
            return [
                "ler_estado_corpo",
            ]

        if tipo == "mapeamento_capacidades":
            return [
                "ler_arquivo",
            ]

        if tipo == "limites":
            return [
                "ler_arquivo",
            ]

        if tipo == "seguranca_arquitetural":
            return [
                "ler_arquivo",
            ]

        if tipo == "integridade":
            return [
                "ler_arquivo",
            ]

        return []

    # ============================================================
    # LEITURA DOS COMPONENTES DECLARADOS
    # ============================================================

    def _investigar_arquivos(
        self,
    ) -> list[dict[str, Any]]:
        componentes_resposta = (
            self.autorrepresentacao.componentes()
        )

        if componentes_resposta.get("estado") != "conhecido":
            return [
                {
                    "fonte": "ler_arquivo",
                    "sucesso": False,
                    "estado": "sem_evidencia",
                    "arquivo": None,
                    "conteudo": None,
                    "erro": (
                        "Os componentes declarados não estão "
                        "disponíveis para selecionar arquivos."
                    ),
                }
            ]

        componentes = componentes_resposta.get(
            "valor",
            []
        )

        evidencias: list[dict[str, Any]] = []

        if not isinstance(
            componentes,
            list,
        ):
            return evidencias

        for componente in componentes:
            if not isinstance(
                componente,
                dict,
            ):
                continue

            arquivo = componente.get(
                "arquivo_principal"
            )

            componente_id = componente.get(
                "id"
            )

            if not isinstance(
                arquivo,
                str,
            ) or not arquivo.strip():
                continue

            resultado = self._executar_fonte(
                "ler_arquivo",
                arquivo=arquivo,
            )

            resultado["componente"] = componente_id
            evidencias.append(
                resultado
            )

        return evidencias

    # ============================================================
    # EXECUÇÃO CONTROLADA
    # ============================================================

    def _executar_fonte(
        self,
        nome: str,
        **argumentos: Any,
    ) -> dict[str, Any]:
        resultado = self.gerenciador.executar(
            nome,
            **argumentos,
        )

        sucesso = bool(
            getattr(
                resultado,
                "sucesso",
                False,
            )
        )

        valor = getattr(
            resultado,
            "resultado",
            None,
        )

        erro = getattr(
            resultado,
            "erro",
            None,
        )

        if isinstance(
            valor,
            str,
        ) and len(valor) > MAX_EVIDENCIA_CHARS:
            valor = (
                valor[:MAX_EVIDENCIA_CHARS]
                + "\n[conteúdo truncado pela investigação]"
            )

        if isinstance(
            valor,
            list,
        ):
            valor = list(valor)

        return {
            "fonte": nome,
            "sucesso": sucesso,
            "estado": (
                "evidencia_disponivel"
                if sucesso
                else "falha_fonte"
            ),
            "argumentos": dict(argumentos),
            "resultado": valor,
            "erro": erro,
        }

    # ============================================================
    # BARREIRAS
    # ============================================================

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "Hipóteses ainda não são formuladas pela investigação."
        )

    def incorporar_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A investigação não incorpora evidência ao conhecimento."
        )

    def modificar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A investigação não modifica a arquitetura."
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "investigacao_interna_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    investigador = InvestigacaoInternaNixal()

    investigacao = {
        "necessidade": "conhecer_dependencias_arquiteturais",
        "pergunta": (
            "Quais relações de dependência existem entre os "
            "componentes da minha arquitetura?"
        ),
        "tipo_investigacao": "mapeamento_arquitetural",
    }

    print("=" * 60)
    print("NIXAL — INVESTIGAÇÃO INTERNA 56.4.11")
    print("=" * 60)
    print()
    print(investigador.executar(investigacao))


if __name__ == "__main__":
    main()
