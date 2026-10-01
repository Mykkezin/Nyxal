#!/usr/bin/env python3

"""
NIXAL — LEITOR DA PLANTA

Microetapa 56.4.3

Responsabilidade:
    Ler a planta_nixal/planta.json e expor uma interface somente
    de leitura para a futura autorrepresentação da Nixal.

Princípios:
1. A planta é a única fonte desta camada.
2. O leitor não modifica a planta.
3. O leitor não inventa componentes, capacidades, sensores ou fatos.
4. Informação ausente deve ser retornada como "desconhecido".
5. O leitor não executa capacidades.
6. O leitor não consulta a internet nem outras fontes externas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARQUIVO_PLANTA = (
    Path(__file__).resolve().parent
    / "planta_nixal"
    / "planta.json"
)


class LeitorPlantaNixal:
    """Interface somente de leitura da planta real da Nixal."""

    def __init__(
        self,
        caminho: Path = ARQUIVO_PLANTA,
    ) -> None:
        self.caminho = Path(caminho)
        self._planta = self._carregar_e_validar()

    # ============================================================
    # CARREGAMENTO
    # ============================================================

    def _carregar_e_validar(self) -> dict[str, Any]:
        if not self.caminho.exists():
            raise FileNotFoundError(
                f"Planta não encontrada: {self.caminho}"
            )

        try:
            with self.caminho.open(
                "r",
                encoding="utf-8",
            ) as arquivo:
                dados = json.load(arquivo)

        except json.JSONDecodeError as erro:
            raise ValueError(
                f"A planta contém JSON inválido: {erro}"
            ) from erro

        if not isinstance(dados, dict):
            raise ValueError(
                "A raiz da planta precisa ser um objeto JSON."
            )

        return dados

    # ============================================================
    # ACESSO CONTROLADO
    # ============================================================

    def planta_completa(self) -> dict[str, Any]:
        """
        Retorna uma cópia profunda da planta.

        O chamador nunca recebe a estrutura interna mutável.
        """
        return json.loads(
            json.dumps(
                self._planta,
                ensure_ascii=False,
            )
        )

    def identidade(self) -> dict[str, Any]:
        valor = self._planta.get("identidade", {})

        if not isinstance(valor, dict):
            return {}

        return dict(valor)

    def estado_atual(self) -> dict[str, Any]:
        valor = self._planta.get("estado_atual", {})

        if not isinstance(valor, dict):
            return {}

        return json.loads(
            json.dumps(
                valor,
                ensure_ascii=False,
            )
        )

    def componentes(self) -> list[dict[str, Any]]:
        valor = self._planta.get("componentes", [])

        if not isinstance(valor, list):
            return []

        return json.loads(
            json.dumps(
                valor,
                ensure_ascii=False,
            )
        )

    def obter_componente(
        self,
        componente_id: str,
    ) -> dict[str, Any] | None:
        for componente in self.componentes():
            if componente.get("id") == componente_id:
                return componente

        return None

    def dependencias(self) -> list[dict[str, Any]]:
        arquitetura = self._planta.get(
            "dependencias",
            [],
        )

        # Compatibilidade: a planta atual mantém os componentes em
        # "componentes" e pode receber dependências futuramente.
        if not isinstance(arquitetura, list):
            arquitetura = []

        return json.loads(
            json.dumps(
                arquitetura,
                ensure_ascii=False,
            )
        )

    def dependencias_componente(
        self,
        componente_id: str,
    ) -> list[dict[str, Any]]:
        dependencias = self.dependencias()

        return [
            dependencia
            for dependencia in dependencias
            if dependencia.get("origem") == componente_id
        ]

    def capacidades(self) -> list[str]:
        valor = self._planta.get(
            "capacidades_conhecidas",
            [],
        )

        if not isinstance(valor, list):
            return []

        return list(
            item
            for item in valor
            if isinstance(item, str)
        )

    def limites(self) -> list[str]:
        valor = self._planta.get(
            "limites_conhecidos",
            [],
        )

        if not isinstance(valor, list):
            return []

        return list(
            item
            for item in valor
            if isinstance(item, str)
        )

    def regras_modificacao(self) -> dict[str, Any]:
        valor = self._planta.get(
            "regras_modificacao",
            {},
        )

        if not isinstance(valor, dict):
            return {}

        return json.loads(
            json.dumps(
                valor,
                ensure_ascii=False,
            )
        )

    def regra_modificacao(
        self,
        parte: str,
    ) -> Any:
        regras = self.regras_modificacao()

        return regras.get(parte)

    # ============================================================
    # CONSULTAS DE AUTORREPRESENTAÇÃO
    # ============================================================

    def consultar(
        self,
        consulta: str,
    ) -> dict[str, Any]:
        """
        Responde somente com informação presente explicitamente
        na planta.

        Não há inferência externa nesta camada.
        """

        texto = (
            consulta
            .strip()
            .lower()
        )

        if texto in {
            "quem e voce?",
            "quem é você?",
            "quem é voce?",
        }:
            return {
                "sucesso": True,
                "estado": "conhecido",
                "origem": "planta_nixal",
                "valor": self.identidade(),
            }

        if texto in {
            "quais componentes existem?",
            "quais componentes existem em você?",
            "quais sao seus componentes?",
            "quais são seus componentes?",
        }:
            return {
                "sucesso": True,
                "estado": "conhecido",
                "origem": "planta_nixal",
                "valor": self.componentes(),
            }

        if texto in {
            "quais capacidades você possui?",
            "quais capacidades voce possui?",
            "quais sao suas capacidades?",
            "quais são suas capacidades?",
        }:
            return {
                "sucesso": True,
                "estado": "conhecido",
                "origem": "planta_nixal",
                "valor": self.capacidades(),
            }

        if texto in {
            "quais sao seus limites?",
            "quais são seus limites?",
            "quais limitações você conhece?",
            "quais limitacoes voce conhece?",
        }:
            return {
                "sucesso": True,
                "estado": "conhecido",
                "origem": "planta_nixal",
                "valor": self.limites(),
            }

        if texto in {
            "a planta pode ser modificada?",
            "voce pode modificar a planta?",
            "você pode modificar a planta?",
        }:
            return {
                "sucesso": True,
                "estado": "conhecido",
                "origem": "planta_nixal",
                "valor": {
                    "planta": self.regra_modificacao("planta"),
                    "pode_modificar": (
                        self.regra_modificacao("planta")
                        != "somente_leitura"
                    ),
                },
            }

        if texto in {
            "qual e a versao da arquitetura?",
            "qual é a versão da arquitetura?",
            "qual a versão da arquitetura?",
        }:
            identidade = self.identidade()

            return {
                "sucesso": True,
                "estado": "conhecido",
                "origem": "planta_nixal",
                "valor": identidade.get(
                    "versao_arquitetura"
                ),
            }

        prefixos_componente = (
            "qual a funcao do componente ",
            "qual é a função do componente ",
            "qual a função do componente ",
        )

        for prefixo in prefixos_componente:
            if texto.startswith(prefixo):
                componente_id = (
                    texto[len(prefixo):]
                    .strip()
                )

                componente = self.obter_componente(
                    componente_id
                )

                if componente is None:
                    return {
                        "sucesso": True,
                        "estado": "desconhecido",
                        "origem": "planta_nixal",
                        "valor": None,
                    }

                return {
                    "sucesso": True,
                    "estado": "conhecido",
                    "origem": "planta_nixal",
                    "valor": componente.get("funcao"),
                }

        prefixos_componente_objeto = (
            "o componente ",
            "componente ",
        )

        for prefixo in prefixos_componente_objeto:
            if texto.startswith(prefixo):
                componente_id = (
                    texto[len(prefixo):]
                    .strip()
                    .rstrip("?")
                )

                componente = self.obter_componente(
                    componente_id
                )

                if componente is None:
                    return {
                        "sucesso": True,
                        "estado": "desconhecido",
                        "origem": "planta_nixal",
                        "valor": None,
                    }

                return {
                    "sucesso": True,
                    "estado": "conhecido",
                    "origem": "planta_nixal",
                    "valor": componente,
                }

        # Qualquer consulta não prevista explicitamente é desconhecida.
        return {
            "sucesso": True,
            "estado": "desconhecido",
            "origem": "planta_nixal",
            "valor": None,
        }


def main() -> None:
    leitor = LeitorPlantaNixal()

    print("=" * 60)
    print("NIXAL — LEITOR DA PLANTA 56.4.3")
    print("=" * 60)

    print()
    print("Identidade:")
    print(
        json.dumps(
            leitor.identidade(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("Componentes:")
    print(
        json.dumps(
            leitor.componentes(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("Capacidades:")
    print(
        json.dumps(
            leitor.capacidades(),
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("Consulta:")
    print(
        json.dumps(
            leitor.consultar(
                "Quais componentes existem?"
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
