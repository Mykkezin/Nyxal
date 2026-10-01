#!/usr/bin/env python3

"""
NIXAL — MODELO DE DEPENDÊNCIAS

Microetapa 56.3.12

Distingue dois tipos de dependência entre etapas:

1. dados     -> a etapa precisa do resultado produzido por outra;
2. temporal  -> a etapa apenas precisa ocorrer depois de outra.

A estrutura legada ``depende_de`` continua sendo aceita como união
compatível entre as duas categorias.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DependenciasPasso:
    dados: list[int] = field(default_factory=list)
    temporais: list[int] = field(default_factory=list)

    @property
    def todas(self) -> list[int]:
        resultado: list[int] = []

        for valor in [*self.dados, *self.temporais]:
            if valor not in resultado:
                resultado.append(valor)

        return resultado


class DependenciasNixal:

    MARCADORES_CONSUMO = (
        "selecionado",
        "selecionada",
        "selecionados",
        "selecionadas",
        "escolhido",
        "escolhida",
        "escolhidos",
        "escolhidas",
        "selecao",
        "seleção",
        "a partir da selecao",
        "a partir da seleção",
        "com base na selecao",
        "com base na seleção",
        "informacao selecionada",
        "informação selecionada",
        "dados selecionados",
        "estado selecionado",
        "arquivo selecionado",
    )

    MARCADORES_SEQUENCIA = (
        "depois",
        "entao",
        "em seguida",
        "a seguir",
        "posteriormente",
        "apos isso",
        "na sequencia",
        "na sequência",
        "logo depois",
    )

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        texto = texto.lower()

        substituicoes = {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }

        for origem, destino in substituicoes.items():
            texto = texto.replace(origem, destino)

        texto = re.sub(r"[^a-z0-9_.-]+", " ", texto)
        return texto.strip()

    @classmethod
    def _contem_marcador(cls, texto: str, marcadores: tuple[str, ...]) -> bool:
        normalizado = cls._normalizar_texto(texto)

        for marcador in marcadores:
            marcador_normalizado = cls._normalizar_texto(marcador)

            if re.search(
                rf"(?<![a-z0-9]){re.escape(marcador_normalizado)}(?![a-z0-9])",
                normalizado,
            ):
                return True

        return False

    @staticmethod
    def normalizar_lista(
        indice_passo: int,
        dependencias: Any,
    ) -> dict[str, Any]:
        if not isinstance(dependencias, list):
            return {
                "sucesso": False,
                "dependencias": [],
                "erro": (
                    f"As dependências do passo {indice_passo} "
                    "precisam ser uma lista."
                ),
            }

        valores: list[int] = []

        for dependencia in dependencias:
            if not isinstance(dependencia, int):
                return {
                    "sucesso": False,
                    "dependencias": [],
                    "erro": (
                        f"A dependência '{dependencia}' do passo "
                        f"{indice_passo} não é inteira."
                    ),
                }

            valores.append(dependencia)

        # Compatibilidade com planos antigos que possam ter usado índice 0.
        if 0 in valores:
            valores = [valor + 1 for valor in valores]

        normalizadas: list[int] = []

        for valor in valores:
            if valor not in normalizadas:
                normalizadas.append(valor)

        for dependencia in normalizadas:
            if dependencia < 1:
                return {
                    "sucesso": False,
                    "dependencias": [],
                    "erro": (
                        f"A dependência {dependencia} do passo "
                        f"{indice_passo} é inválida."
                    ),
                }

            if dependencia >= indice_passo:
                return {
                    "sucesso": False,
                    "dependencias": [],
                    "erro": (
                        f"O passo {indice_passo} depende de {dependencia}, "
                        "mas só pode depender de etapas anteriores."
                    ),
                }

        return {
            "sucesso": True,
            "dependencias": normalizadas,
            "erro": None,
        }

    def classificar_dependencia(
        self,
        indice_passo: int,
        dependencia: int,
        passo_atual: dict[str, Any],
        passos: list[dict[str, Any]],
        necessidade_original: str | None = None,
    ) -> str:
        if dependencia < 1 or dependencia > len(passos):
            raise ValueError("Dependência fora do plano.")

        passo_origem = passos[dependencia - 1]

        if passo_atual.get("tipo") == "contexto":
            return "dados"

        if passo_origem.get("tipo") == "contexto":
            return "dados"

        necessidade_atual = str(
            passo_atual.get("necessidade", "")
        )

        if self._contem_marcador(
            necessidade_atual,
            self.MARCADORES_CONSUMO,
        ):
            return "dados"

        if necessidade_original and self._contem_marcador(
            necessidade_original,
            self.MARCADORES_CONSUMO,
        ):
            if dependencia in passo_atual.get("depende_de", []):
                return "dados"

        if necessidade_original and self._contem_marcador(
            necessidade_original,
            self.MARCADORES_SEQUENCIA,
        ):
            if dependencia == indice_passo - 1:
                return "temporal"

        # Na ausência de evidência clara de temporalidade, conservamos
        # a dependência como dado por segurança.
        return "dados"

    def inferir(
        self,
        indice_passo: int,
        passo: dict[str, Any],
        passos: list[dict[str, Any]],
        necessidade_original: str | None = None,
    ) -> dict[str, Any]:
        legado = passo.get("depende_de", [])

        resultado_legado = self.normalizar_lista(
            indice_passo,
            legado,
        )

        if not resultado_legado["sucesso"]:
            return {
                "sucesso": False,
                "dependencias": {
                    "dados": [],
                    "temporais": [],
                },
                "depende_de": [],
                "erro": resultado_legado["erro"],
            }

        dados_existentes = passo.get("dependencias", {})

        if not isinstance(dados_existentes, dict):
            dados_existentes = {}

        dados_declarados = dados_existentes.get("dados", [])
        temporais_declarados = dados_existentes.get("temporais", [])

        norm_dados = self.normalizar_lista(
            indice_passo,
            dados_declarados,
        )
        norm_temporais = self.normalizar_lista(
            indice_passo,
            temporais_declarados,
        )

        if not norm_dados["sucesso"]:
            return {
                "sucesso": False,
                "dependencias": {
                    "dados": [],
                    "temporais": [],
                },
                "depende_de": [],
                "erro": norm_dados["erro"],
            }

        if not norm_temporais["sucesso"]:
            return {
                "sucesso": False,
                "dependencias": {
                    "dados": [],
                    "temporais": [],
                },
                "depende_de": [],
                "erro": norm_temporais["erro"],
            }

        dados: list[int] = list(norm_dados["dependencias"])
        temporais: list[int] = list(norm_temporais["dependencias"])

        declaradas = set(dados) | set(temporais)

        for dependencia in resultado_legado["dependencias"]:
            if dependencia in declaradas:
                continue

            categoria = self.classificar_dependencia(
                indice_passo,
                dependencia,
                passo,
                passos,
                necessidade_original,
            )

            if categoria == "dados":
                dados.append(dependencia)
            else:
                temporais.append(dependencia)

        # Uma dependência não pode aparecer nos dois grupos.
        temporais = [
            valor
            for valor in temporais
            if valor not in dados
        ]

        return {
            "sucesso": True,
            "dependencias": {
                "dados": dados,
                "temporais": temporais,
            },
            "depende_de": [
                *dados,
                *[valor for valor in temporais if valor not in dados],
            ],
            "erro": None,
        }

    def validar_plano(
        self,
        passos: list[dict[str, Any]],
        necessidade_original: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(passos, list):
            return {
                "sucesso": False,
                "passos": [],
                "erro": "Os passos precisam ser uma lista.",
            }

        atualizados: list[dict[str, Any]] = []

        for indice, passo in enumerate(passos, start=1):
            if not isinstance(passo, dict):
                return {
                    "sucesso": False,
                    "passos": [],
                    "erro": f"O passo {indice} não é um objeto.",
                }

            inferido = self.inferir(
                indice,
                passo,
                passos,
                necessidade_original,
            )

            if not inferido["sucesso"]:
                return {
                    "sucesso": False,
                    "passos": [],
                    "erro": inferido["erro"],
                }

            copia = dict(passo)
            copia["dependencias"] = inferido["dependencias"]
            copia["depende_de"] = inferido["depende_de"]

            atualizados.append(copia)

        return {
            "sucesso": True,
            "passos": atualizados,
            "erro": None,
        }


def main() -> None:
    gerente = DependenciasNixal()

    plano_arquivo = [
        {
            "ordem": 1,
            "necessidade": "Listar os arquivos do projeto",
            "depende_de": [],
            "tipo": "acao",
        },
        {
            "ordem": 2,
            "necessidade": "Selecionar o arquivo capacidades_nixal.json da lista",
            "depende_de": [1],
            "tipo": "contexto",
        },
        {
            "ordem": 3,
            "necessidade": "Ler o arquivo selecionado",
            "depende_de": [2],
            "tipo": "acao",
        },
    ]

    plano_corpo = [
        {
            "ordem": 1,
            "necessidade": "Consultar o estado atual do corpo computacional da Nixal",
            "depende_de": [],
            "tipo": "acao",
        },
        {
            "ordem": 2,
            "necessidade": "Consultar os eventos registrados na memória corporal",
            "depende_de": [1],
            "tipo": "acao",
        },
    ]

    plano_misto = [
        {
            "ordem": 1,
            "necessidade": "Listar os arquivos do projeto",
            "depende_de": [],
            "tipo": "acao",
        },
        {
            "ordem": 2,
            "necessidade": "Consultar os arquivos depois da listagem",
            "depende_de": [1],
            "tipo": "acao",
        },
        {
            "ordem": 3,
            "necessidade": "Ler o arquivo selecionado",
            "depende_de": [2],
            "tipo": "acao",
        },
    ]

    resultados = {
        "arquivo": gerente.validar_plano(plano_arquivo),
        "corpo": gerente.validar_plano(
            plano_corpo,
            necessidade_original=(
                "Quero saber como está meu corpo e depois consultar "
                "os eventos registrados na memória corporal."
            ),
        ),
        "misto": gerente.validar_plano(plano_misto),
    }

    plano_invalido = gerente.validar_plano(
        [
            {
                "ordem": 1,
                "necessidade": "A",
                "depende_de": [1],
                "tipo": "acao",
            }
        ]
    )

    resultados["invalido"] = plano_invalido

    resumo = {
        "arquivo": resultados["arquivo"]["passos"],
        "corpo": resultados["corpo"]["passos"],
        "misto": resultados["misto"]["passos"],
        "invalido": resultados["invalido"],
        "passou": (
            resultados["arquivo"]["sucesso"]
            and resultados["corpo"]["sucesso"]
            and resultados["misto"]["sucesso"]
            and not resultados["invalido"]["sucesso"]
            and resultados["arquivo"]["passos"][1]["dependencias"]
            == {"dados": [1], "temporais": []}
            and resultados["arquivo"]["passos"][2]["dependencias"]
            == {"dados": [2], "temporais": []}
            and resultados["corpo"]["passos"][1]["dependencias"]
            == {"dados": [], "temporais": [1]}
        ),
    }

    import json

    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
