#!/usr/bin/env python3

"""
NIXAL — MEMÓRIA PERSISTENTE DE INVESTIGAÇÃO

Microetapa 56.4.15

Responsabilidade:
    Persistir investigações, evidências, hipóteses, testes e
    avaliações em memória durável.

Princípios:
1. A memória é separada da planta arquitetural.
2. A memória pode registrar experiências explicitamente.
3. Um registro persistido não altera a planta.
4. O registro preserva o ciclo completo recebido.
5. Registros duplicados não são gravados novamente.
6. A identidade do registro é determinística.
7. A memória não executa capacidades.
8. A memória não modifica a arquitetura.
9. Um registro salvo não vira automaticamente conhecimento permanente.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


VERSAO_MEMORIA = "56.4.15"

ARQUIVO_MEMORIA_PADRAO = (
    Path(__file__).resolve().parent
    / "memoria_investigacao_nixal.json"
)


class MemoriaInvestigacaoNixal:
    """Armazenamento persistente de ciclos de investigação."""

    FONTE = "memoria_investigacao_nixal"

    def __init__(
        self,
        caminho: Path = ARQUIVO_MEMORIA_PADRAO,
    ) -> None:
        self.caminho = Path(caminho)
        self._dados = self._carregar()

    # ============================================================
    # CARREGAMENTO
    # ============================================================

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho.exists():
            return self._estrutura_vazia()

        try:
            dados = json.loads(
                self.caminho.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return self._estrutura_vazia()

        if not isinstance(
            dados,
            dict,
        ):
            return self._estrutura_vazia()

        if dados.get("versao") != VERSAO_MEMORIA:
            return self._estrutura_vazia()

        registros = dados.get(
            "registros",
            [],
        )

        if not isinstance(
            registros,
            list,
        ):
            return self._estrutura_vazia()

        return {
            "versao": VERSAO_MEMORIA,
            "registros": copy.deepcopy(
                registros
            ),
        }

    @staticmethod
    def _estrutura_vazia() -> dict[str, Any]:
        return {
            "versao": VERSAO_MEMORIA,
            "registros": [],
        }

    # ============================================================
    # IDENTIDADE DO REGISTRO
    # ============================================================

    @staticmethod
    def _id_registro(
        ciclo: dict[str, Any],
    ) -> str:
        canonico = json.dumps(
            ciclo,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        return hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()

    # ============================================================
    # VALIDAÇÃO
    # ============================================================

    @staticmethod
    def _validar_ciclo(
        ciclo: Any,
    ) -> tuple[bool, str | None]:
        if not isinstance(
            ciclo,
            dict,
        ):
            return False, "Ciclo precisa ser um objeto."

        obrigatorios = (
            "hipotese",
            "estado_atual",
            "historico",
            "testes",
            "avaliacoes",
            "conhecimento_permanente",
        )

        for campo in obrigatorios:
            if campo not in ciclo:
                return (
                    False,
                    f"Campo obrigatório ausente: {campo}",
                )

        if not isinstance(
            ciclo.get("hipotese"),
            str,
        ) or not ciclo.get(
            "hipotese",
            "",
        ).strip():
            return False, "Texto da hipótese inválido."

        if not isinstance(
            ciclo.get("estado_atual"),
            str,
        ):
            return False, "Estado atual inválido."

        if not isinstance(
            ciclo.get("historico"),
            list,
        ):
            return False, "Histórico inválido."

        if not isinstance(
            ciclo.get("testes"),
            list,
        ):
            return False, "Lista de testes inválida."

        if not isinstance(
            ciclo.get("avaliacoes"),
            list,
        ):
            return False, "Lista de avaliações inválida."

        if ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return (
                False,
                "Memória de investigação não pode marcar "
                "conhecimento permanente como verdadeiro.",
            )

        return True, None

    # ============================================================
    # REGISTRO
    # ============================================================

    def registrar(
        self,
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        valido, erro = self._validar_ciclo(
            ciclo
        )

        if not valido:
            return self._negado(
                erro or "Ciclo inválido."
            )

        ciclo_copia = copy.deepcopy(
            ciclo
        )

        registro_id = self._id_registro(
            ciclo_copia
        )

        for registro in self._dados[
            "registros"
        ]:
            if (
                isinstance(
                    registro,
                    dict,
                )
                and registro.get("id")
                == registro_id
            ):
                return {
                    "sucesso": True,
                    "estado": "ja_existente",
                    "origem": self.FONTE,
                    "valor": copy.deepcopy(
                        registro
                    ),
                }

        registro = {
            "id": registro_id,
            "versao_memoria": VERSAO_MEMORIA,
            "ciclo": ciclo_copia,
        }

        self._dados[
            "registros"
        ].append(
            registro
        )

        self._salvar()

        return {
            "sucesso": True,
            "estado": "persistido",
            "origem": self.FONTE,
            "valor": copy.deepcopy(
                registro
            ),
        }

    # ============================================================
    # LEITURA
    # ============================================================

    def listar(
        self,
    ) -> list[dict[str, Any]]:
        return copy.deepcopy(
            self._dados.get(
                "registros",
                [],
            )
        )

    def quantidade(self) -> int:
        return len(
            self._dados.get(
                "registros",
                [],
            )
        )

    def obter(
        self,
        registro_id: str,
    ) -> dict[str, Any] | None:
        for registro in self._dados.get(
            "registros",
            [],
        ):
            if (
                isinstance(
                    registro,
                    dict,
                )
                and registro.get("id")
                == registro_id
            ):
                return copy.deepcopy(
                    registro
                )

        return None

    def recarregar(self) -> dict[str, Any]:
        self._dados = self._carregar()

        return {
            "sucesso": True,
            "estado": "recarregado",
            "origem": self.FONTE,
            "valor": {
                "quantidade": self.quantidade(),
            },
        }

    # ============================================================
    # PROTEÇÕES
    # ============================================================

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória não executa capacidades."
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória não modifica a arquitetura."
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "Persistência de investigação não promove "
            "conhecimento permanente."
        )

    # ============================================================
    # PERSISTÊNCIA ATÔMICA
    # ============================================================

    def _salvar(self) -> None:
        self.caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        texto = json.dumps(
            self._dados,
            ensure_ascii=False,
            indent=2,
        )

        temporario = self.caminho.with_suffix(
            self.caminho.suffix + ".tmp"
        )

        temporario.write_text(
            texto,
            encoding="utf-8",
        )

        os.replace(
            temporario,
            self.caminho,
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "memoria_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    memoria = MemoriaInvestigacaoNixal()

    exemplo = {
        "hipotese": (
            "Exemplo de hipótese persistível."
        ),
        "estado_atual": "provisoria",
        "historico": [
            {
                "de": None,
                "para": "provisoria",
                "evento": "hipotese_criada",
            }
        ],
        "testes": [],
        "avaliacoes": [],
        "conhecimento_permanente": False,
    }

    print("=" * 60)
    print("NIXAL — MEMÓRIA DE INVESTIGAÇÃO 56.4.15")
    print("=" * 60)
    print()
    print(
        memoria.registrar(
            exemplo
        )
    )
    print()
    print(
        "Registros:",
        memoria.quantidade(),
    )


if __name__ == "__main__":
    main()
