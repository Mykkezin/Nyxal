#!/usr/bin/env python3

"""
NIXAL — MEMÓRIA PERSISTENTE DE CONHECIMENTO CANDIDATO

Responsabilidade:
    Persistir candidatos de conhecimento produzidos pelo ciclo de
    consolidação, sem promovê-los automaticamente a conhecimento
    permanente e sem modificar a arquitetura.

Princípios:
1. O candidato precisa vir de uma consolidação válida.
2. A memória preserva o candidato sem alterar seu conteúdo.
3. Registros duplicados não são gravados novamente.
4. A identidade do registro é determinística.
5. Persistência não significa conhecimento permanente.
6. A memória não promove conhecimento.
7. A memória não modifica a arquitetura.
8. A memória não executa capacidades.
9. A escrita usa substituição atômica.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


VERSAO_MEMORIA = "1.0"

ARQUIVO_MEMORIA_PADRAO = (
    Path(__file__).resolve().parent
    / "memoria_conhecimento_nixal.json"
)


class MemoriaConhecimentoNixal:
    """Armazenamento persistente de candidatos de conhecimento."""

    FONTE = "memoria_conhecimento_nixal"

    def __init__(
        self,
        caminho: Path = ARQUIVO_MEMORIA_PADRAO,
    ) -> None:
        self.caminho = Path(caminho)
        self._dados = self._carregar()

    @staticmethod
    def _estrutura_vazia() -> dict[str, Any]:
        return {
            "versao": VERSAO_MEMORIA,
            "registros": [],
        }

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho.exists():
            return self._estrutura_vazia()

        try:
            dados = json.loads(
                self.caminho.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return self._estrutura_vazia()

        if not isinstance(dados, dict):
            return self._estrutura_vazia()

        if dados.get("versao") != VERSAO_MEMORIA:
            return self._estrutura_vazia()

        registros = dados.get("registros", [])
        if not isinstance(registros, list):
            return self._estrutura_vazia()

        return {
            "versao": VERSAO_MEMORIA,
            "registros": copy.deepcopy(registros),
        }

    @staticmethod
    def _id_registro(candidato: dict[str, Any]) -> str:
        canonico = json.dumps(
            candidato,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _validar_candidato(
        candidato: Any,
    ) -> tuple[bool, str | None]:
        if not isinstance(candidato, dict):
            return False, "Candidato precisa ser um objeto."

        texto = candidato.get("texto")
        tipo = candidato.get("tipo")
        origem = candidato.get("origem")

        if not isinstance(texto, str) or not texto.strip():
            return False, "Texto do candidato inválido."

        if not isinstance(tipo, str) or not tipo.strip():
            return False, "Tipo do candidato inválido."

        if not isinstance(origem, dict):
            return False, "Origem do candidato inválida."

        if origem.get("estado") != "suportada":
            return (
                False,
                "Somente candidatos provenientes de uma "
                "avaliação suportada podem ser persistidos.",
            )

        if candidato.get("conhecimento_permanente") is not False:
            return (
                False,
                "O candidato não pode marcar conhecimento "
                "permanente como verdadeiro.",
            )

        if candidato.get("gravado") is not False:
            return (
                False,
                "O candidato de entrada precisa estar marcado "
                "como não gravado.",
            )

        return True, None

    def registrar(
        self,
        candidato: dict[str, Any],
    ) -> dict[str, Any]:
        valido, erro = self._validar_candidato(candidato)

        if not valido:
            return self._negado(
                erro or "Candidato inválido."
            )

        candidato_copia = copy.deepcopy(candidato)
        registro_id = self._id_registro(candidato_copia)

        for registro in self._dados["registros"]:
            if (
                isinstance(registro, dict)
                and registro.get("registro_id") == registro_id
            ):
                return {
                    "sucesso": True,
                    "estado": "ja_existente",
                    "origem": self.FONTE,
                    "valor": copy.deepcopy(registro),
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                }

        registro = {
            "registro_id": registro_id,
            "candidato": candidato_copia,
            "conhecimento_permanente": False,
            "gravado": True,
        }

        self._dados["registros"].append(registro)
        self._salvar()

        return {
            "sucesso": True,
            "estado": "persistido",
            "origem": self.FONTE,
            "valor": copy.deepcopy(registro),
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def listar(self) -> list[dict[str, Any]]:
        return copy.deepcopy(
            self._dados.get("registros", [])
        )

    def quantidade(self) -> int:
        return len(
            self._dados.get("registros", [])
        )

    def obter(
        self,
        registro_id: str,
    ) -> dict[str, Any] | None:
        for registro in self._dados.get("registros", []):
            if (
                isinstance(registro, dict)
                and registro.get("registro_id") == registro_id
            ):
                return copy.deepcopy(registro)
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

    @staticmethod
    def _negado(motivo: str) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "memoria_conhecimento_nixal",
            "valor": None,
            "motivo": motivo,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória de candidatos não promove "
            "conhecimento permanente."
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória de candidatos não modifica a arquitetura."
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória de candidatos não executa capacidades."
        )

    def _salvar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)

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
