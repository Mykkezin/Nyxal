#!/usr/bin/env python3

"""
NYXAL — CONTRATO DE ARTEFATO DE DESENVOLVIMENTO

Define o contexto mínimo que acompanha um artefato recebido pelo
pipeline. O contrato é declarativo: não contém comandos executáveis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


OPERACOES_PERMITIDAS = frozenset(
    {
        "analise",
        "py_compile",
    }
)

TIPOS_PERMITIDOS = frozenset(
    {
        "python",
        "texto",
    }
)


@dataclass(frozen=True)
class ContratoArtefatoNixal:
    versao_contrato: int
    nome: str
    objetivo: str
    tipo: str
    arquivo: str
    operacoes_permitidas: tuple[str, ...]
    executar: bool

    @classmethod
    def carregar(
        cls,
        caminho_manifesto: str | Path,
    ) -> "ContratoArtefatoNixal":
        caminho = Path(caminho_manifesto)

        try:
            dados = json.loads(
                caminho.read_text(
                    encoding="utf-8"
                )
            )
        except UnicodeDecodeError as erro:
            raise ValueError(
                "manifesto_nao_utf8"
            ) from erro
        except json.JSONDecodeError as erro:
            raise ValueError(
                "manifesto_json_invalido"
            ) from erro

        if not isinstance(dados, dict):
            raise ValueError(
                "manifesto_deve_ser_objeto"
            )

        obrigatorios = (
            "versao_contrato",
            "nome",
            "objetivo",
            "tipo",
            "arquivo",
            "operacoes_permitidas",
            "executar",
        )

        ausentes = [
            campo
            for campo in obrigatorios
            if campo not in dados
        ]

        if ausentes:
            raise ValueError(
                "campos_obrigatorios_ausentes:"
                + ",".join(ausentes)
            )

        versao = dados["versao_contrato"]

        if versao != 1:
            raise ValueError(
                "versao_contrato_nao_suportada"
            )

        nome = dados["nome"]
        objetivo = dados["objetivo"]
        tipo = dados["tipo"]
        arquivo = dados["arquivo"]
        operacoes = dados["operacoes_permitidas"]
        executar = dados["executar"]

        if not isinstance(nome, str) or not nome.strip():
            raise ValueError(
                "nome_invalido"
            )

        if not isinstance(objetivo, str) or not objetivo.strip():
            raise ValueError(
                "objetivo_invalido"
            )

        if tipo not in TIPOS_PERMITIDOS:
            raise ValueError(
                "tipo_nao_permitido"
            )

        if not isinstance(arquivo, str) or not arquivo.strip():
            raise ValueError(
                "arquivo_invalido"
            )

        caminho_arquivo = Path(arquivo)

        if (
            caminho_arquivo.is_absolute()
            or ".." in caminho_arquivo.parts
        ):
            raise ValueError(
                "arquivo_fora_da_entrada"
            )

        if not isinstance(operacoes, list):
            raise ValueError(
                "operacoes_permitidas_deve_ser_lista"
            )

        if not operacoes:
            raise ValueError(
                "nenhuma_operacao_permitida"
            )

        if any(
            not isinstance(op, str)
            or op not in OPERACOES_PERMITIDAS
            for op in operacoes
        ):
            raise ValueError(
                "operacao_nao_permitida"
            )

        if not isinstance(executar, bool):
            raise ValueError(
                "executar_deve_ser_booleano"
            )

        if executar:
            raise ValueError(
                "execucao_de_codigo_nao_permitida"
            )

        return cls(
            versao_contrato=versao,
            nome=nome.strip(),
            objetivo=objetivo.strip(),
            tipo=tipo,
            arquivo=arquivo,
            operacoes_permitidas=tuple(
                operacoes
            ),
            executar=executar,
        )
