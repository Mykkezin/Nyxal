"""Normalização isolada de evidências para o Grafo Operacional.

O módulo é deliberadamente puro: não acessa Runtime, planta, rede,
persistência, Git ou mecanismos de autorização.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


TIPOS = frozenset(
    {
        "observacao",
        "persistencia",
        "transformacao",
        "evidencia_experimental",
    }
)

AUTORIDADES = frozenset({"observacional", "experimental"})

FONTES = frozenset({"habitat", "persistencia", "delta", "ae4"})

PROVENIENCIAS = {
    "habitat": "nixal_habitat.py",
    "persistencia": "nixal_persistencia_operacional.py",
    "delta": "nixal_delta.py",
    "ae4": "nixal_ciclo_evolucao_ae4.py",
}

AUTORIDADES_PROIBIDAS = frozenset(
    {"arquitetural", "autorizado", "integrado"}
)


@dataclass(frozen=True)
class RelacaoOperacional:
    origem: str
    destino: str | None
    tipo: str
    evidencia: str
    proveniencia: str
    ciclo: str | None
    instante: str
    autoridade: str


@dataclass(frozen=True)
class RejeicaoNormalizacao:
    codigo: str
    campo: str | None
    motivo: str
    regra: str


@dataclass(frozen=True)
class ResultadoNormalizacao:
    sucesso: bool
    relacao: RelacaoOperacional | None = None
    rejeicao: RejeicaoNormalizacao | None = None

    @classmethod
    def aceitar(cls, relacao: RelacaoOperacional) -> "ResultadoNormalizacao":
        return cls(sucesso=True, relacao=relacao)

    @classmethod
    def rejeitar(cls, rejeicao: RejeicaoNormalizacao) -> "ResultadoNormalizacao":
        return cls(sucesso=False, rejeicao=rejeicao)


class NormalizadorOperacional:
    """Normaliza evidências sem efeitos colaterais."""

    def normalizar(
        self,
        evidencia: Mapping[str, Any],
        contexto: Mapping[str, Any] | None = None,
    ) -> ResultadoNormalizacao:
        if not isinstance(evidencia, Mapping):
            return self._rejeitar(
                "entrada_invalida",
                None,
                "A evidência deve ser um mapeamento.",
                "O5.1",
            )

        fonte = evidencia.get("fonte")
        if fonte not in FONTES:
            return self._rejeitar(
                "fonte_invalida",
                "fonte",
                "A fonte deve pertencer ao conjunto fechado.",
                "O6.3",
            )

        if "autoridade" in evidencia:
            autoridade = evidencia.get("autoridade")
            regra = "O5.1"
            if autoridade in AUTORIDADES_PROIBIDAS:
                return self._rejeitar(
                    "autoridade_proibida",
                    "autoridade",
                    "A autoridade é atribuída exclusivamente pelo normalizador.",
                    regra,
                )
            return self._rejeitar(
                "autoridade_externa",
                "autoridade",
                "A evidência bruta não pode declarar a autoridade da relação.",
                regra,
            )

        for campo in ("origem", "proveniencia", "instante"):
            valor = evidencia.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                return self._rejeitar(
                    "campo_obrigatorio_ausente",
                    campo,
                    f"O campo obrigatório '{campo}' está ausente ou vazio.",
                    "O5.1",
                )

        proveniencia_esperada = PROVENIENCIAS[fonte]
        if evidencia["proveniencia"] != proveniencia_esperada:
            return self._rejeitar(
                "proveniencia_invalida",
                "proveniencia",
                "A proveniência não corresponde à fonte declarada.",
                "O6.2",
            )

        if not self._timestamp_valido(evidencia["instante"]):
            return self._rejeitar(
                "instante_invalido",
                "instante",
                "O instante deve ser um timestamp ISO 8601 válido.",
                "O5.1",
            )

        evidencia_value = evidencia.get("evidencia")
        evidencia_hash = evidencia.get("evidencia_hash")
        if (evidencia_value is None) == (evidencia_hash is None):
            return self._rejeitar(
                "evidencia_ambigua",
                "evidencia",
                "Deve existir exatamente uma evidência textual ou hash da evidência.",
                "O5.1",
            )

        evidencia_final = evidencia_value if evidencia_value is not None else evidencia_hash
        if not isinstance(evidencia_final, str) or not evidencia_final.strip():
            return self._rejeitar(
                "evidencia_invalida",
                "evidencia",
                "A evidência deve ser uma string não vazia.",
                "O5.1",
            )

        tipo_declarado = evidencia.get("tipo")
        tipos_esperados = {
            "habitat": "observacao",
            "persistencia": "persistencia",
            "delta": "transformacao",
            "ae4": None,
        }
        tipo_esperado = tipos_esperados[fonte]
        if tipo_declarado is not None and tipo_esperado is not None:
            if tipo_declarado != tipo_esperado:
                return self._rejeitar(
                    "tipo_invalido",
                    "tipo",
                    "O tipo declarado não corresponde ao mapeamento determinístico da fonte.",
                    "O6.2",
                )
        elif tipo_declarado is not None and tipo_esperado is None:
            if tipo_declarado not in {"observacao", "evidencia_experimental"}:
                return self._rejeitar(
                    "tipo_invalido",
                    "tipo",
                    "O tipo declarado do AE4 está fora do domínio permitido.",
                    "O5.1",
                )

        if fonte == "habitat":
            tipo = "observacao"
            autoridade = "observacional"
            ciclo = None
        elif fonte == "persistencia":
            tipo = "persistencia"
            autoridade = "observacional"
            ciclo_resultado = self._resolver_ciclo(evidencia)
            if isinstance(ciclo_resultado, RejeicaoNormalizacao):
                return ResultadoNormalizacao.rejeitar(ciclo_resultado)
            ciclo = ciclo_resultado
        elif fonte == "delta":
            tipo = "transformacao"
            autoridade = "observacional"
            ciclo_resultado = self._resolver_ciclo(evidencia)
            if isinstance(ciclo_resultado, RejeicaoNormalizacao):
                return ResultadoNormalizacao.rejeitar(ciclo_resultado)
            ciclo = ciclo_resultado
        else:
            return self._normalizar_ae4(evidencia, evidencia_final)

        destino = self._destino(evidencia)
        if destino is _REJEICAO:
            return self._rejeitar(
                "destino_invalido",
                "destino",
                "O destino, quando presente, deve ser diretamente demonstrado.",
                "O6.2",
            )

        return self._emitir(
            origem=evidencia["origem"],
            destino=destino,
            tipo=tipo,
            evidencia=evidencia_final,
            proveniencia=evidencia["proveniencia"],
            ciclo=ciclo,
            instante=evidencia["instante"],
            autoridade=autoridade,
        )

    def _normalizar_ae4(
        self,
        evidencia: Mapping[str, Any],
        evidencia_final: str,
    ) -> ResultadoNormalizacao:
        if self._ae4_experimental_valido(evidencia):
            tipo = "evidencia_experimental"
            autoridade = "experimental"
        else:
            tipo = "observacao"
            autoridade = "observacional"

        destino = self._destino(evidencia)
        if destino is _REJEICAO:
            return self._rejeitar(
                "destino_invalido",
                "destino",
                "O destino, quando presente, deve ser diretamente demonstrado.",
                "O6.2",
            )

        return self._emitir(
            origem=evidencia["origem"],
            destino=destino,
            tipo=tipo,
            evidencia=evidencia_final,
            proveniencia=evidencia["proveniencia"],
            ciclo=self._resolver_ciclo_ou_rejeitar(evidencia),
            instante=evidencia["instante"],
            autoridade=autoridade,
        )

    @staticmethod
    def _ae4_experimental_valido(evidencia: Mapping[str, Any]) -> bool:
        return (
            evidencia.get("relacao_confirmada") is True
            and bool(evidencia.get("vinculo_causal_persistido"))
            and evidencia.get("avaliacao_concluida") is True
            and bool(evidencia.get("resultado_classificado"))
            and evidencia.get("stable_modificada") is False
            and evidencia.get("integracao_executada") is False
        )

    @staticmethod
    def _resolver_ciclo_ou_rejeitar(evidencia: Mapping[str, Any]) -> str | None:
        resultado = NormalizadorOperacional._resolver_ciclo(evidencia)
        if isinstance(resultado, RejeicaoNormalizacao):
            raise ValueError(resultado.motivo)
        return resultado

    @staticmethod
    def _resolver_ciclo(
        evidencia: Mapping[str, Any],
    ) -> str | None | RejeicaoNormalizacao:
        if "ciclo_id" in evidencia:
            valor = evidencia["ciclo_id"]
        elif "ciclo" in evidencia:
            valor = evidencia["ciclo"]
        else:
            return None

        if valor is None:
            return None
        if isinstance(valor, str) and valor.strip():
            return valor
        return RejeicaoNormalizacao(
            codigo="ciclo_invalido",
            campo="ciclo",
            motivo="O ciclo informado pela fonte não possui formato válido.",
            regra="O5.1",
        )

    @staticmethod
    def _destino(evidencia: Mapping[str, Any]) -> str | None | object:
        if "destino" not in evidencia:
            return None
        destino = evidencia["destino"]
        if destino is None:
            return None
        if isinstance(destino, str) and destino.strip():
            if evidencia.get("destino_demonstrado") is True:
                return destino
            return _REJEICAO
        return _REJEICAO

    @staticmethod
    def _timestamp_valido(valor: str) -> bool:
        try:
            datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return False
        return True

    @staticmethod
    def _rejeitar(
        codigo: str,
        campo: str | None,
        motivo: str,
        regra: str,
    ) -> ResultadoNormalizacao:
        return ResultadoNormalizacao.rejeitar(
            RejeicaoNormalizacao(
                codigo=codigo,
                campo=campo,
                motivo=motivo,
                regra=regra,
            )
        )

    @staticmethod
    def _emitir(
        *,
        origem: str,
        destino: str | None,
        tipo: str,
        evidencia: str,
        proveniencia: str,
        ciclo: str | None,
        instante: str,
        autoridade: str,
    ) -> ResultadoNormalizacao:
        if tipo not in TIPOS:
            return NormalizadorOperacional._rejeitar(
                "tipo_invalido",
                "tipo",
                "Tipo fora do vocabulário fechado.",
                "O5.1",
            )
        if autoridade not in AUTORIDADES:
            return NormalizadorOperacional._rejeitar(
                "autoridade_invalida",
                "autoridade",
                "Autoridade fora do vocabulário permitido.",
                "O5.1",
            )
        return ResultadoNormalizacao.aceitar(
            RelacaoOperacional(
                origem=origem,
                destino=destino,
                tipo=tipo,
                evidencia=evidencia,
                proveniencia=proveniencia,
                ciclo=ciclo,
                instante=instante,
                autoridade=autoridade,
            )
        )


_REJEICAO = object()
