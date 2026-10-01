#!/usr/bin/env python3

"""
NIXAL — AUTORREPRESENTAÇÃO

Microetapa 56.4.4

Responsabilidade:
    Integrar o LeitorPlantaNixal a uma interface interna formal de
    autorrepresentação.

Esta camada:
1. usa somente a planta real através do leitor;
2. não modifica a planta;
3. não executa capacidades;
4. não inicia conversação;
5. não consulta fontes externas;
6. diferencia informação conhecida de desconhecida;
7. expõe uma interface que poderá ser usada futuramente por
   raciocínio, diagnóstico e evolução controlada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from leitor_planta_nixal import LeitorPlantaNixal


class AutorreprentacaoNixal:
    """
    Interface interna de autorrepresentação da Nixal.

    O nome da classe preserva a grafia usada no projeto:
    "AutorreprentacaoNixal".
    """

    FONTE = "planta_nixal"

    def __init__(
        self,
        caminho_planta: Path | None = None,
    ) -> None:
        if caminho_planta is None:
            self.leitor = LeitorPlantaNixal()
        else:
            self.leitor = LeitorPlantaNixal(
                caminho_planta
            )

    # ============================================================
    # IDENTIDADE
    # ============================================================

    def identidade(self) -> dict[str, Any]:
        return self._resposta_conhecida(
            self.leitor.identidade()
        )

    # ============================================================
    # COMPONENTES
    # ============================================================

    def componentes(self) -> dict[str, Any]:
        return self._resposta_conhecida(
            self.leitor.componentes()
        )

    def componente(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        componente = self.leitor.obter_componente(
            componente_id
        )

        if componente is None:
            return self._resposta_desconhecida()

        return self._resposta_conhecida(
            componente
        )

    def funcao_componente(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        componente = self.leitor.obter_componente(
            componente_id
        )

        if componente is None:
            return self._resposta_desconhecida()

        return self._resposta_conhecida(
            componente.get("funcao")
        )

    # ============================================================
    # DEPENDÊNCIAS
    # ============================================================

    def dependencias(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        componente = self.leitor.obter_componente(
            componente_id
        )

        if componente is None:
            return self._resposta_desconhecida()

        return self._resposta_conhecida(
            self.leitor.dependencias_componente(
                componente_id
            )
        )

    # ============================================================
    # CAPACIDADES
    # ============================================================

    def capacidades(self) -> dict[str, Any]:
        return self._resposta_conhecida(
            self.leitor.capacidades()
        )

    def possui_capacidade(
        self,
        nome: str,
    ) -> dict[str, Any]:
        capacidades = self.leitor.capacidades()

        if nome in capacidades:
            return self._resposta_conhecida(
                True
            )

        return self._resposta_desconhecida()

    # ============================================================
    # LIMITES
    # ============================================================

    def limites(self) -> dict[str, Any]:
        return self._resposta_conhecida(
            self.leitor.limites()
        )

    # ============================================================
    # REGRAS DE MODIFICAÇÃO
    # ============================================================

    def regras_modificacao(self) -> dict[str, Any]:
        return self._resposta_conhecida(
            self.leitor.regras_modificacao()
        )

    def pode_modificar(
        self,
        parte: str,
    ) -> dict[str, Any]:
        regra = self.leitor.regra_modificacao(
            parte
        )

        if regra is None:
            return self._resposta_desconhecida()

        permitido = (
            regra != "somente_leitura"
            and regra != "protegido"
        )

        return self._resposta_conhecida(
            {
                "parte": parte,
                "regra": regra,
                "pode_modificar": permitido,
            }
        )

    # ============================================================
    # ESTADO DECLARADO DA ARQUITETURA
    # ============================================================

    def estado_arquitetura(self) -> dict[str, Any]:
        return self._resposta_conhecida(
            self.leitor.estado_atual()
        )

    # ============================================================
    # CONSULTA ESTRUTURADA
    # ============================================================

    def consultar(
        self,
        consulta: str,
    ) -> dict[str, Any]:
        """
        Delegação controlada para o leitor da planta.

        Esta função não transforma a autorrepresentação em uma camada
        de conversa. Ela apenas disponibiliza a informação declarada
        pela planta para outros componentes internos.
        """

        resposta = self.leitor.consultar(
            consulta
        )

        if not isinstance(
            resposta,
            dict,
        ):
            return {
                "sucesso": False,
                "estado": "desconhecido",
                "origem": self.FONTE,
                "valor": None,
                "erro": "Resposta inválida do leitor da planta.",
            }

        resposta = dict(resposta)

        resposta.setdefault(
            "origem",
            self.FONTE,
        )

        return resposta

    # ============================================================
    # SNAPSHOT
    # ============================================================

    def snapshot(self) -> dict[str, Any]:
        """
        Retorna uma visão estruturada da autorrepresentação atual.

        O snapshot é somente leitura e contém apenas informações
        provenientes da planta.
        """

        return {
            "sucesso": True,
            "estado": "conhecido",
            "origem": self.FONTE,
            "identidade": self.leitor.identidade(),
            "estado_arquitetura": self.leitor.estado_atual(),
            "componentes": self.leitor.componentes(),
            "capacidades": self.leitor.capacidades(),
            "limites": self.leitor.limites(),
            "regras_modificacao": (
                self.leitor.regras_modificacao()
            ),
        }

    # ============================================================
    # RESPOSTAS
    # ============================================================

    def _resposta_conhecida(
        self,
        valor: Any,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "conhecido",
            "origem": self.FONTE,
            "valor": valor,
        }

    def _resposta_desconhecida(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "desconhecido",
            "origem": self.FONTE,
            "valor": None,
        }


def main() -> None:
    autorrepresentacao = AutorreprentacaoNixal()

    print("=" * 60)
    print("NIXAL — AUTORREPRESENTAÇÃO 56.4.4")
    print("=" * 60)

    print()
    print("Identidade:")
    print(
        autorrepresentacao.identidade()
    )

    print()
    print("Componentes:")
    print(
        autorrepresentacao.componentes()
    )

    print()
    print("Capacidades:")
    print(
        autorrepresentacao.capacidades()
    )

    print()
    print("Snapshot:")
    print(
        autorrepresentacao.snapshot()
    )


if __name__ == "__main__":
    main()
