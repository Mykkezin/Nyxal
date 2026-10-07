from __future__ import annotations

import hashlib

from nixal_agregador_operacional import agregar
from nixal_analise_operacional import analisar
from nixal_candidato_aprendizado_operacional import formular
from nixal_comparacao_evidencias_operacional import comparar
from nixal_evidencia_operacional import consolidar as consolidar_evidencia
from nixal_fechamento_cadeia_operacional import ORDEM_CADEIA, fechar
from nixal_handoff_o15_llc import preparar as preparar_handoff
from nixal_normalizador_operacional import NormalizadorOperacional
from nixal_padroes_recorrentes_operacional import detectar
from nixal_qualificacao_evidencia_operacional import qualificar
from nixal_reutilizacao_evidencia_operacional import reutilizar


def _artefato(identidade: str, objeto: object) -> str:
    material = f"{identidade}|{repr(objeto)}".encode("utf-8")
    return identidade + "-" + hashlib.sha256(material).hexdigest()[:16]


def _relacao_comum():
    resultado = NormalizadorOperacional().normalizar(
        {
            "fonte": "habitat",
            "origem": "A",
            "proveniencia": "nixal_habitat.py",
            "instante": "2026-10-07T00:00:00+00:00",
            "evidencia": "observacao-comum",
            "destino": "B",
            "destino_demonstrado": True,
        }
    )
    assert resultado.sucesso is True
    assert resultado.relacao is not None
    return resultado.relacao


def _relacao_exclusiva():
    resultado = NormalizadorOperacional().normalizar(
        {
            "fonte": "persistencia",
            "origem": "B",
            "proveniencia": "nixal_persistencia_operacional.py",
            "instante": "2026-10-07T00:00:01+00:00",
            "evidencia": "persistencia-exclusiva",
            "destino": "C",
            "destino_demonstrado": True,
            "ciclo_id": "c2",
        }
    )
    assert resultado.sucesso is True
    assert resultado.relacao is not None
    return resultado.relacao


def test_serie_o9_o15_handoff_llc_fechada_sem_aprendizado() -> None:
    relacao_comum = _relacao_comum()
    relacao_exclusiva = _relacao_exclusiva()

    # O9: O8 -> AnaliseOperacional -> EvidenciaOperacional.
    grafo_1 = agregar([relacao_comum]).sucesso
    grafo_2 = agregar([relacao_comum, relacao_exclusiva]).sucesso
    assert grafo_1 is not None
    assert grafo_2 is not None

    analise_1 = analisar(grafo_1).sucesso
    analise_2 = analisar(grafo_2).sucesso
    assert analise_1 is not None
    assert analise_2 is not None

    o9_1 = consolidar_evidencia(analise_1).sucesso
    o9_2 = consolidar_evidencia(analise_2).sucesso
    assert o9_1 is not None
    assert o9_2 is not None
    assert o9_1.identidade != o9_2.identidade

    # O10: qualificação estrutural, sem interpretação.
    o10_1 = qualificar(o9_1).sucesso
    o10_2 = qualificar(o9_2).sucesso
    assert o10_1 is not None and o10_2 is not None
    assert o10_1.estado == "qualificada"
    assert o10_2.estado == "qualificada"

    # O11: reutilização explícita de uma evidência qualificada.
    o11 = reutilizar(o9_2, o10_2, "tipo", "observacao")
    assert o11.reutilizada is True
    assert o11.resultado is not None
    assert o11.resultado.relacoes == (relacao_comum,)

    # O12: a comparação reconhece a relação comum sem alterar entradas.
    o12 = comparar(o10_1, o10_2)
    assert o12.sobreposicao is True
    assert o12.total_intersecao == 1
    assert o12.relacoes_primeira == (relacao_comum,)
    assert o12.relacoes_segunda == (relacao_comum, relacao_exclusiva)

    # O13: recorrência somente entre evidências distintas.
    o13 = detectar((o10_1, o10_2))
    assert o13.total_padroes == 1
    assert o13.padroes[0].evidencias_distintas == (
        o9_1.identidade,
        o9_2.identidade,
    )
    assert o13.padroes[0].frequencia_evidencias == 2

    # O14: recorrência vira somente candidato, nunca aprendizado.
    o14 = formular(o13.padroes)
    assert len(o14) == 1
    candidato = o14[0]
    assert candidato.estado == "candidato"
    assert "não representa aprendizado" in candidato.justificativa

    # O15: fecha exatamente O9 -> O14.
    cadeia = (
        {"etapa": "O9", "identidade": o9_1.identidade, "estado": "consolidada"},
        {"etapa": "O10", "identidade": o10_1.identidade, "estado": o10_1.estado},
        {
            "etapa": "O11",
            "identidade": _artefato("O11", o11.resultado),
            "estado": "reutilizada",
        },
        {
            "etapa": "O12",
            "identidade": _artefato("O12", o12),
            "estado": "comparada",
        },
        {
            "etapa": "O13",
            "identidade": _artefato("O13", o13),
            "estado": "recorrente",
        },
        {
            "etapa": "O14",
            "identidade": candidato.identidade,
            "estado": candidato.estado,
            "autorizacao_integracao": False,
            "integrado": False,
        },
    )

    o15 = fechar(cadeia)
    assert o15.estado == "fechado"
    assert o15.cadeia_fechada is True
    assert o15.handoff_preparado is True
    assert o15.etapas == ORDEM_CADEIA
    assert o15.identidade_candidato == candidato.identidade

    # O15 -> LLC: envelope de encaminhamento, não execução de aprendizado.
    handoff = preparar_handoff(o15)
    assert handoff.estado == "preparado"
    assert handoff.destino == "llc"
    assert handoff.etapas == ORDEM_CADEIA
    assert handoff.identidade_candidato == candidato.identidade
    assert handoff.aprendizado_executado is False
    assert handoff.autorizacao_integracao is False
    assert handoff.integracao_executada is False

    assert candidato.estado == "candidato"
    assert handoff.aprendizado_executado is False
    assert handoff.integracao_executada is False


if __name__ == "__main__":
    test_serie_o9_o15_handoff_llc_fechada_sem_aprendizado()
    print("SERIE_O9_O15_LLC_HANDOFF_OK")
    print("APRENDIZADO: NAO_EXECUTADO")
    print("INTEGRACAO: NAO_EXECUTADA")
    print("CADEIA: FECHADA")
