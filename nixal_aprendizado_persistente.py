#!/usr/bin/env python3
"""
NYXAL — APRENDIZADO PERSISTENTE ENTRE CICLOS

Nível 8 / M3 — Learning Loop.

Responsabilidade:
    transformar uma experiência avaliada em conhecimento estruturado,
    cristalizar uma representação compacta e disponibilizar esse
    conhecimento para o ciclo seguinte.

Princípios:
- aprendizado é persistente;
- conhecimento é derivado apenas da experiência recebida;
- cristal é uma representação compacta, não uma nova verdade;
- nenhuma alteração arquitetural é executada;
- o aprendizado pode ser consultado pelo próximo ciclo;
- registros são idempotentes por identidade determinística.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

VERSAO_APRENDIZADO = "8.0.0"


class AprendizadoPersistenteNixal:
    """Memória mínima e auditável para aprendizado entre ciclos."""

    FONTE = "aprendizado_persistente_nixal"

    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)
        self._dados = self._carregar()

    def _estrutura_vazia(self) -> dict[str, Any]:
        return {"versao": VERSAO_APRENDIZADO, "aprendizados": []}

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

        if dados.get("versao") != VERSAO_APRENDIZADO:
            return self._estrutura_vazia()

        aprendizados = dados.get("aprendizados")

        if not isinstance(aprendizados, list):
            return self._estrutura_vazia()

        return {
            "versao": VERSAO_APRENDIZADO,
            "aprendizados": copy.deepcopy(aprendizados),
        }

    @staticmethod
    def _id_aprendizado(
        experiencia_base: dict[str, Any],
    ) -> str:
        canonico = json.dumps(
            experiencia_base,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _cristalizar(
        experiencia: dict[str, Any],
        avaliacao: dict[str, Any],
    ) -> dict[str, Any]:
        avaliacao_nome = str(
            avaliacao.get("avaliacao", "inconclusiva")
        )
        acao = str(
            experiencia.get("acao", "desconhecida")
        )
        resultado = str(
            experiencia.get("resultado", "desconhecido")
        )

        return {
            "conceito": "experiencia_runtime",
            "essencia": (
                f"A ação {acao} produziu {resultado} "
                f"com avaliação {avaliacao_nome}."
            ),
            "relacoes": [
                f"acao→{acao}",
                f"resultado→{resultado}",
                f"avaliacao→{avaliacao_nome}",
            ],
            "incerteza": (
                "O aprendizado descreve somente o resultado "
                "observado neste ciclo; não representa verdade absoluta."
            ),
        }

    def registrar(
        self,
        ciclo_id: str,
        experiencia: dict[str, Any],
        avaliacao: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(experiencia, dict):
            return self._erro("experiencia inválida.")

        if not isinstance(avaliacao, dict):
            return self._erro("avaliacao inválida.")

        if not isinstance(ciclo_id, str) or not ciclo_id.strip():
            return self._erro("ciclo_id inválido.")

        aprendizado_base = {
            "ciclo_origem": ciclo_id,
            "experiencia": copy.deepcopy(experiencia),
            "avaliacao": copy.deepcopy(avaliacao),
        }

        aprendizado_id = self._id_aprendizado(
            aprendizado_base
        )

        for registro in self._dados["aprendizados"]:
            if (
                isinstance(registro, dict)
                and registro.get("id") == aprendizado_id
            ):
                return {
                    "sucesso": True,
                    "estado": "ja_existente",
                    "origem": self.FONTE,
                    "valor": copy.deepcopy(registro),
                    "novo": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                }

        conhecimento = {
            "id": aprendizado_id,
            "ciclo_origem": ciclo_id,
            "tipo": "resultado_experiencial",
            "texto": (
                f"A ação {experiencia.get('acao')} foi observada "
                f"como {experiencia.get('resultado')} e avaliada "
                f"como {avaliacao.get('avaliacao')}."
            ),
            "evidencias": [
                copy.deepcopy(experiencia),
                copy.deepcopy(avaliacao),
            ],
            "confianca": (
                "observacional"
                if avaliacao.get("avaliacao") == "sucesso"
                else "limitada"
            ),
        }

        registro = {
            "id": aprendizado_id,
            "versao": VERSAO_APRENDIZADO,
            "ciclo_origem": ciclo_id,
            "experiencia": copy.deepcopy(experiencia),
            "avaliacao": copy.deepcopy(avaliacao),
            "conhecimento": conhecimento,
            "cristal": self._cristalizar(
                experiencia,
                avaliacao,
            ),
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

        self._dados["aprendizados"].append(registro)
        self._dados["aprendizados"] = (
            self._dados["aprendizados"][-100:]
        )
        self._salvar()

        return {
            "sucesso": True,
            "estado": "aprendizado_persistido",
            "origem": self.FONTE,
            "valor": copy.deepcopy(registro),
            "novo": True,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def consultar_ultimo(self) -> dict[str, Any] | None:
        if not self._dados["aprendizados"]:
            return None
        return copy.deepcopy(self._dados["aprendizados"][-1])

    def contexto_para_proximo_ciclo(self) -> dict[str, Any]:
        ultimo = self.consultar_ultimo()

        if ultimo is None:
            return {
                "disponivel": False,
                "fonte": self.FONTE,
                "motivo": "Nenhum aprendizado persistido.",
                "aplicado_no_ciclo_atual": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            }

        conhecimento = ultimo.get("conhecimento", {})
        cristal = ultimo.get("cristal", {})

        experiencia_anterior = ultimo.get("experiencia")
        avaliacao_anterior = ultimo.get("avaliacao")

        return {
            "disponivel": True,
            "aprendizado_id": ultimo.get("id"),
            "ciclo_origem": ultimo.get("ciclo_origem"),
            "conhecimento": copy.deepcopy(conhecimento),
            "cristal": copy.deepcopy(cristal),
            "experiencia_anterior": (
                copy.deepcopy(experiencia_anterior)
                if isinstance(experiencia_anterior, dict)
                else {}
            ),
            "avaliacao_anterior": (
                copy.deepcopy(avaliacao_anterior)
                if isinstance(avaliacao_anterior, dict)
                else {}
            ),
            "acao_anterior": (
                experiencia_anterior.get("acao")
                if isinstance(experiencia_anterior, dict)
                else None
            ),
            "resultado_anterior": (
                experiencia_anterior.get("resultado")
                if isinstance(experiencia_anterior, dict)
                else None
            ),
            "aplicado_no_ciclo_atual": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def quantidade(self) -> int:
        return len(self._dados["aprendizados"])

    def _salvar(self) -> None:
        self.caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporario = self.caminho.with_name(
            self.caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                self._dados,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(
            temporario,
            self.caminho,
        )

    @staticmethod
    def _erro(motivo: str) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "entrada_invalida",
            "origem": "aprendizado_persistente_nixal",
            "motivo": motivo,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }
