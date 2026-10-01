#!/usr/bin/env python3

"""
NIXAL — REGISTRO DE OPERAÇÕES SOBRE CONTEXTO

Microetapa 56.3.10

Objetivos:

1. Carregar o catálogo formal de operações sobre contexto.
2. Validar a estrutura das operações.
3. Expor especificações das operações.
4. Permitir descobrir quais operações de contexto existem.
5. Manter separação entre:
   - capacidades: ações executáveis no sistema;
   - operações de contexto: transformações sobre informação
     que já está disponível.
6. Não executar operações neste módulo.

Por enquanto o catálogo contém somente:

    selecionar
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ARQUIVO_OPERACOES = Path(
    "operacoes_contexto_nixal.json"
)


@dataclass
class OperacaoContexto:
    nome: str
    descricao: str
    objetivo: str
    tipo_entrada: str
    tipo_saida: str
    argumentos: dict[str, Any] = field(
        default_factory=dict
    )
    regras: list[str] = field(
        default_factory=list
    )
    exemplos: list[str] = field(
        default_factory=list
    )


class OperacoesContextoNixal:

    def __init__(
        self,
        arquivo: Path = ARQUIVO_OPERACOES,
    ) -> None:

        self.arquivo = arquivo

        self.operacoes = (
            self._carregar_catalogo()
        )

        self.mapa_operacoes = {
            operacao.nome: operacao
            for operacao in self.operacoes
        }

    # ============================================================
    # NORMALIZAÇÃO
    # ============================================================

    @staticmethod
    def _texto(
        valor: Any,
        campo: str,
    ) -> str:

        if not isinstance(
            valor,
            str,
        ):

            raise ValueError(
                f"O campo '{campo}' precisa "
                "ser uma string."
            )

        valor = valor.strip()

        if not valor:

            raise ValueError(
                f"O campo '{campo}' não pode "
                "ser vazio."
            )

        return valor

    @staticmethod
    def _lista_textos(
        valor: Any,
        campo: str,
    ) -> list[str]:

        if not isinstance(
            valor,
            list,
        ):

            raise ValueError(
                f"O campo '{campo}' precisa "
                "ser uma lista."
            )

        resultado = []

        for item in valor:

            if not isinstance(
                item,
                str,
            ):

                raise ValueError(
                    f"Todos os itens de '{campo}' "
                    "precisam ser strings."
                )

            item = item.strip()

            if item:

                resultado.append(
                    item
                )

        return resultado

    @staticmethod
    def _objeto(
        valor: Any,
        campo: str,
    ) -> dict[str, Any]:

        if not isinstance(
            valor,
            dict,
        ):

            raise ValueError(
                f"O campo '{campo}' precisa "
                "ser um objeto."
            )

        return dict(
            valor
        )

    # ============================================================
    # CARREGAMENTO
    # ============================================================

    def _carregar_catalogo(
        self,
    ) -> list[OperacaoContexto]:

        if not self.arquivo.exists():

            raise FileNotFoundError(
                "Arquivo "
                "operacoes_contexto_nixal.json "
                "não encontrado."
            )

        try:

            with self.arquivo.open(
                "r",
                encoding="utf-8",
            ) as arquivo:

                dados = json.load(
                    arquivo
                )

        except json.JSONDecodeError as erro:

            raise ValueError(
                "operacoes_contexto_nixal.json "
                f"possui JSON inválido: {erro}"
            ) from erro

        if not isinstance(
            dados,
            list,
        ):

            raise ValueError(
                "operacoes_contexto_nixal.json "
                "precisa conter uma lista."
            )

        operacoes = []

        for indice, item in enumerate(
            dados,
            start=1,
        ):

            if not isinstance(
                item,
                dict,
            ):

                raise ValueError(
                    f"A operação {indice} "
                    "não é um objeto JSON."
                )

            nome = self._texto(
                item.get("nome"),
                "nome",
            )

            descricao = self._texto(
                item.get("descricao"),
                "descricao",
            )

            objetivo = self._texto(
                item.get("objetivo"),
                "objetivo",
            )

            tipo_entrada = self._texto(
                item.get("tipo_entrada"),
                "tipo_entrada",
            )

            tipo_saida = self._texto(
                item.get("tipo_saida"),
                "tipo_saida",
            )

            argumentos = self._objeto(
                item.get(
                    "argumentos",
                    {},
                ),
                "argumentos",
            )

            regras = self._lista_textos(
                item.get(
                    "regras",
                    [],
                ),
                "regras",
            )

            exemplos = self._lista_textos(
                item.get(
                    "exemplos",
                    [],
                ),
                "exemplos",
            )

            if nome in {
                operacao.nome
                for operacao in operacoes
            }:

                raise ValueError(
                    f"A operação '{nome}' "
                    "está duplicada."
                )

            operacoes.append(
                OperacaoContexto(
                    nome=nome,
                    descricao=descricao,
                    objetivo=objetivo,
                    tipo_entrada=tipo_entrada,
                    tipo_saida=tipo_saida,
                    argumentos=argumentos,
                    regras=regras,
                    exemplos=exemplos,
                )
            )

        if not operacoes:

            raise ValueError(
                "Nenhuma operação de contexto "
                "válida foi encontrada."
            )

        return operacoes

    # ============================================================
    # CONSULTA
    # ============================================================

    def listar_operacoes(
        self,
    ) -> list[dict[str, Any]]:

        resultado = []

        for operacao in self.operacoes:

            resultado.append(
                {
                    "nome": operacao.nome,
                    "descricao": operacao.descricao,
                    "objetivo": operacao.objetivo,
                    "tipo_entrada": operacao.tipo_entrada,
                    "tipo_saida": operacao.tipo_saida,
                    "argumentos": operacao.argumentos,
                    "regras": operacao.regras,
                    "exemplos": operacao.exemplos,
                }
            )

        return resultado

    def obter_operacao(
        self,
        nome: str,
    ) -> OperacaoContexto | None:

        if not isinstance(
            nome,
            str,
        ):

            return None

        nome = nome.strip()

        if not nome:

            return None

        return self.mapa_operacoes.get(
            nome
        )

    def obter_especificacao(
        self,
        nome: str,
    ) -> dict[str, Any] | None:

        operacao = self.obter_operacao(
            nome
        )

        if operacao is None:

            return None

        return {
            "nome": operacao.nome,
            "descricao": operacao.descricao,
            "objetivo": operacao.objetivo,
            "tipo_entrada": operacao.tipo_entrada,
            "tipo_saida": operacao.tipo_saida,
            "argumentos": operacao.argumentos,
            "regras": operacao.regras,
            "exemplos": operacao.exemplos,
        }

    def validar_argumentos(
        self,
        nome: str,
        argumentos: dict[str, Any],
    ) -> dict[str, Any]:

        operacao = self.obter_operacao(
            nome
        )

        if operacao is None:

            return {
                "valido": False,
                "erro": (
                    f"Operação de contexto "
                    f"'{nome}' não existe."
                ),
            }

        if not isinstance(
            argumentos,
            dict,
        ):

            return {
                "valido": False,
                "erro": (
                    "Os argumentos da operação "
                    "precisam ser um objeto."
                ),
            }

        especificacao = (
            operacao.argumentos
        )

        for nome_argumento, contrato in (
            especificacao.items()
        ):

            if not isinstance(
                contrato,
                dict,
            ):

                continue

            obrigatorio = (
                contrato.get(
                    "obrigatorio",
                    False,
                )
            )

            if (
                obrigatorio
                and nome_argumento not in argumentos
            ):

                return {
                    "valido": False,
                    "erro": (
                        f"O argumento obrigatório "
                        f"'{nome_argumento}' não foi fornecido."
                    ),
                }

        return {
            "valido": True,
            "erro": None,
        }


# ================================================================
# MAIN
# ================================================================

def main() -> None:

    registro = (
        OperacoesContextoNixal()
    )

    print()
    print("=" * 60)
    print(
        "NIXAL — OPERAÇÕES SOBRE CONTEXTO"
    )
    print("=" * 60)

    print()

    print(
        "OPERAÇÕES DISPONÍVEIS:"
    )

    for operacao in (
        registro.listar_operacoes()
    ):

        print()
        print(
            f"Nome: {operacao['nome']}"
        )

        print(
            f"Descrição: "
            f"{operacao['descricao']}"
        )

        print(
            f"Objetivo: "
            f"{operacao['objetivo']}"
        )

        print(
            f"Entrada: "
            f"{operacao['tipo_entrada']}"
        )

        print(
            f"Saída: "
            f"{operacao['tipo_saida']}"
        )

        print(
            "Argumentos:"
        )

        print(
            json.dumps(
                operacao["argumentos"],
                ensure_ascii=False,
                indent=2,
            )
        )

        print(
            "Regras:"
        )

        for regra in operacao[
            "regras"
        ]:

            print(
                f"- {regra}"
            )

        print(
            "Exemplos:"
        )

        for exemplo in operacao[
            "exemplos"
        ]:

            print(
                f"- {exemplo}"
            )

    print()
    print("=" * 60)
    print(
        "TESTE DE EXISTÊNCIA DA OPERAÇÃO"
    )
    print("=" * 60)

    especificacao = (
        registro.obter_especificacao(
            "selecionar"
        )
    )

    print(
        json.dumps(
            especificacao,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("=" * 60)
    print(
        "TESTE DE ARGUMENTOS"
    )
    print("=" * 60)

    validacao = (
        registro.validar_argumentos(
            "selecionar",
            {
                "consulta": (
                    "capacidades_nixal.json"
                )
            },
        )
    )

    print(
        json.dumps(
            validacao,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("=" * 60)
    print(
        "TESTE DE OPERAÇÃO INEXISTENTE"
    )
    print("=" * 60)

    inexistente = (
        registro.obter_especificacao(
            "operacao_inexistente"
        )
    )

    print(
        json.dumps(
            {
                "encontrada": (
                    inexistente is not None
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
