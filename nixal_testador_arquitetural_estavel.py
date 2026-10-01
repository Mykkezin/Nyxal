#!/usr/bin/env python3

"""
NIXAL — TESTADOR ARQUITETURAL

Responsabilidade:
    Observar relações de import entre componentes declarados na
    planta_nixal/planta.json e produzir evidência estruturada para
    testes controlados de hipóteses arquiteturais.

Princípios:
1. Somente leitura.
2. Não modifica planta, código ou memória.
3. Não executa capacidades da Nyxal.
4. Não formula nem avalia hipóteses.
5. Resultado determinístico para o mesmo estado dos arquivos.
6. A evidência descreve relações observadas no código.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any


class TestadorArquiteturalNixal:
    """Observa dependências entre componentes declarados."""

    FONTE = "teste_arquitetural"
    VERSAO = "1.0"

    def __init__(
        self,
        planta: Path | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self.base_dir = (
            Path(base_dir)
            if base_dir is not None
            else Path(__file__).resolve().parent
        )

        self.planta = (
            Path(planta)
            if planta is not None
            else self.base_dir / "planta_nixal" / "planta.json"
        )

    def executar(
        self,
        entrada_teste: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(entrada_teste, dict):
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "evidencias": [],
                "motivo": "Entrada de teste precisa ser um objeto.",
            }

        hipotese = entrada_teste.get("hipotese")

        if not isinstance(hipotese, dict):
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "evidencias": [],
                "motivo": "Entrada de teste não contém hipótese válida.",
            }

        if hipotese.get("estado") != "provisoria":
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "evidencias": [],
                "motivo": "A hipótese precisa permanecer provisória.",
            }

        componentes = self._carregar_componentes()

        if not isinstance(componentes, dict):
            return {
                "sucesso": False,
                "estado": "teste_nao_concluido",
                "evidencias": [],
                "motivo": "Não foi possível carregar os componentes da planta.",
            }

        relacoes = self._observar_relacoes(componentes)

        suporte = bool(relacoes)

        evidencias = [
            {
                "fonte": self.FONTE,
                "descricao": (
                    "Relação de dependência entre componentes declarados "
                    "foi observada por análise dos imports do código."
                ),
                "relacoes_observadas": deepcopy(relacoes),
                "quantidade_relacoes": len(relacoes),
            }
        ]

        if not suporte:
            evidencias[0]["descricao"] = (
                "Nenhuma relação de import entre componentes declarados "
                "foi observada no código analisado."
            )

        return {
            "sucesso": True,
            "estado": "observacao_realizada",
            "fonte": self.FONTE,
            "versao_teste": self.VERSAO,
            "evidencias": evidencias,
            "dados_observados": {
                "relacoes_encontradas": deepcopy(relacoes),
                "quantidade_relacoes": len(relacoes),
                "planta possui declaracao_formal_dependencias": (
                    self._planta_declara_dependencias_formais()
                ),
            },
            "suporte": suporte,
            "contraria": False,
            "inconclusivo": False,
        }

    def _carregar_componentes(
        self,
    ) -> dict[str, dict[str, str]] | None:
        try:
            import json

            dados = json.loads(
                self.planta.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            ValueError,
        ):
            return None

        componentes = dados.get("componentes")

        if not isinstance(componentes, list):
            return None

        resultado: dict[str, dict[str, str]] = {}

        for item in componentes:
            if not isinstance(item, dict):
                continue

            componente_id = item.get("id")
            arquivo = item.get("arquivo_principal")

            if not isinstance(componente_id, str):
                continue

            if not isinstance(arquivo, str):
                continue

            resultado[componente_id] = {
                "arquivo": arquivo,
                "modulo": Path(arquivo).stem,
            }

        return resultado

    def _observar_relacoes(
        self,
        componentes: dict[str, dict[str, str]],
    ) -> list[dict[str, str]]:
        modulo_para_componente = {
            dados["modulo"]: componente_id
            for componente_id, dados in componentes.items()
        }

        relacoes: list[dict[str, str]] = []

        for componente_id in sorted(componentes):
            dados_origem = componentes[componente_id]
            caminho = self.base_dir / dados_origem["arquivo"]

            if caminho.suffix != ".py" or not caminho.exists():
                continue

            try:
                arvore = ast.parse(
                    caminho.read_text(
                        encoding="utf-8"
                    ),
                    filename=str(caminho),
                )
            except (
                OSError,
                SyntaxError,
            ):
                continue

            imports: set[str] = set()

            for no in ast.walk(arvore):
                if isinstance(no, ast.Import):
                    for alias in no.names:
                        imports.add(
                            alias.name.split(".")[0]
                        )

                elif isinstance(no, ast.ImportFrom):
                    if no.module:
                        imports.add(
                            no.module.split(".")[0]
                        )

            for modulo_destino in sorted(imports):
                destino = modulo_para_componente.get(
                    modulo_destino
                )

                if destino is None:
                    continue

                relacoes.append(
                    {
                        "origem": componente_id,
                        "arquivo_origem": dados_origem["arquivo"],
                        "destino": destino,
                        "arquivo_destino": componentes[destino]["arquivo"],
                    }
                )

        return relacoes

    def _planta_declara_dependencias_formais(self) -> bool:
        try:
            import json

            dados = json.loads(
                self.planta.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            ValueError,
        ):
            return False

        componentes = dados.get("componentes", [])

        if not isinstance(componentes, list):
            return False

        for item in componentes:
            if not isinstance(item, dict):
                continue

            if (
                "dependencias" in item
                or "depende_de" in item
            ):
                return True

        return False


__all__ = [
    "TestadorArquiteturalNixal",
]
