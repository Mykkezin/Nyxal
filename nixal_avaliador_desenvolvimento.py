#!/usr/bin/env python3

"""
NYXAL — AVALIADOR CONTROLADO DE DESENVOLVIMENTO

Transforma os resultados da análise/validação em uma decisão explícita.
A avaliação é determinística nesta etapa e não executa código recebido.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AvaliacaoDesenvolvimentoNixal:
    aprovado: bool
    criterios: dict[str, bool]
    motivos: list[str]

    @classmethod
    def avaliar(
        cls,
        *,
        contrato: dict,
        validacao_python: dict | None,
    ) -> "AvaliacaoDesenvolvimentoNixal":
        criterios = {
            "contrato_declarativo_valido": bool(
                contrato
            ),
            "execucao_desabilitada": (
                contrato.get("executar") is False
            ),
            "analise_autorizada": (
                "analise"
                in contrato.get(
                    "operacoes_permitidas",
                    [],
                )
            ),
        }

        if contrato.get("tipo") == "python":
            criterios["sintaxe_python_valida"] = (
                validacao_python is not None
                and validacao_python.get("sucesso")
                is True
            )
        else:
            criterios["sintaxe_python_valida"] = True

        motivos = [
            nome
            for nome, passou in criterios.items()
            if not passou
        ]

        return cls(
            aprovado=all(
                criterios.values()
            ),
            criterios=criterios,
            motivos=motivos,
        )

    def como_dict(self) -> dict:
        return {
            "aprovado": self.aprovado,
            "criterios": dict(
                self.criterios
            ),
            "motivos": list(
                self.motivos
            ),
        }
