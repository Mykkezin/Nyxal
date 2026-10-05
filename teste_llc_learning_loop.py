#!/usr/bin/env python3
"""Teste deterministico do LLC.1 -> LLC.2 -> LLC.3."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_learning_loop_causal import LearningLoopCausalNixal
from nixal_runtime import NyxalRuntime


def prioridades():
    return {"sucesso": True, "quantidade": 1, "selecionada": {"necessidade": "estabilidade", "prioridade": "alta"}}


def estado():
    return {"corpo": {"cpu": {"uso_percentual": 20.0, "estado": "normal"}, "memoria": {"uso_percentual": 40.0, "estado": "normal"}}}


def aprendizado(acao, avaliacao):
    return {
        "disponivel": True, "aprendizado_id": "aprendizado-teste",
        "ciclo_origem": "ciclo-anterior",
        "experiencia_anterior": {"acao": acao, "resultado": "resultado_observado"},
        "avaliacao_anterior": {"avaliacao": avaliacao},
        "aplicado_no_ciclo_atual": True, "conhecimento_permanente": False,
        "arquitetura_modificada": False,
    }


def metrica():
    return {
        "nome": "latencia_operacional", "unidade": "ms",
        "fonte": "medicao_controlada_teste", "direcao_melhor": "menor",
        "tolerancia": 1.0, "desenho_experimental": "contraste_controlado_did",
    }


def observacoes():
    return [
        {"id": "obs-1", "intervencao_antes": 100.0, "intervencao_depois": 70.0,
         "controle_antes": 100.0, "controle_depois": 90.0,
         "contrafactual_validado": True, "controle_valido": True, "confundidores_detectados": []},
        {"id": "obs-2", "intervencao_antes": 110.0, "intervencao_depois": 82.0,
         "controle_antes": 108.0, "controle_depois": 96.0,
         "contrafactual_validado": True, "controle_valido": True, "confundidores_detectados": []},
        {"id": "obs-3", "intervencao_antes": 95.0, "intervencao_depois": 65.0,
         "controle_antes": 97.0, "controle_depois": 88.0,
         "contrafactual_validado": True, "controle_valido": True, "confundidores_detectados": []},
    ]


def main():
    llc = LearningLoopCausalNixal()
    sem = llc.selecionar(estado_corpo=estado(), prioridades=prioridades(), aprendizado_anterior=None)
    assert sem["acao"] == "registrar_estado_corpo"
    assert sem["llc"]["influencia_decisoria_comprovada"] is False

    falha = llc.selecionar(
        estado_corpo=estado(), prioridades=prioridades(),
        aprendizado_anterior=aprendizado("registrar_estado_corpo", "falha")
    )
    assert falha["acao"] == "observar_sem_atuar"
    assert falha["llc"]["mudou_escolha"] is True
    assert falha["llc"]["influencia_decisoria_comprovada"] is True
    assert falha["llc"]["causalidade_ambiental_comprovada"] is False

    sucesso = llc.selecionar(
        estado_corpo=estado(), prioridades=prioridades(),
        aprendizado_anterior=aprendizado("registrar_estado_corpo", "sucesso")
    )
    assert sucesso["acao"] == "registrar_estado_corpo"
    assert sucesso["llc"]["mudou_escolha"] is False
    assert sucesso["llc"]["influencia_decisoria_comprovada"] is False

    with TemporaryDirectory() as tmp:
        runtime = NyxalRuntime(
            arquivo_estado=Path(tmp) / "runtime.json",
            arquivo_log=Path(tmp) / "log.json",
            arquivo_memoria_aprendizado=Path(tmp) / "aprendizado.json",
            learning_loop_causal=llc,
        )
        decisao = runtime._decidir(
            estado_corpo=estado(), prioridades=prioridades(),
            aprendizado_anterior=aprendizado("registrar_estado_corpo", "falha")
        )
        assert decisao["acao"] == "observar_sem_atuar"
        acao = runtime._agir(decisao=decisao, estado_corpo=estado())
        assert acao["sucesso"] is True
        assert acao["executada"] is False

    feedback = llc.avaliar_resultado(
        decisao=falha,
        acao_resultado={"sucesso": True, "acao": "observar_sem_atuar", "executada": False},
        resultado_observado={"sucesso": True, "estado": "resultado_observado"},
    )
    assert feedback["ganho_perda_operacional"] == 0.0
    assert feedback["classificacao"] == "neutro_operacional"

    causal = llc.avaliar_consequencia_controlada(
        decisao={**falha, "acao": "registrar_estado_corpo"},
        acao_resultado={"sucesso": True, "acao": "registrar_estado_corpo", "executada": True},
        resultado_observado={"sucesso": True, "estado": "resultado_observado"},
        metrica=metrica(), observacoes=observacoes(),
    )
    assert causal["sucesso"] is True
    assert causal["evidencia_causal_controlada"] is True
    assert causal["causalidade_ambiental_comprovada"] is True
    assert causal["efeito_medio_contrafactual"] < -1.0
    assert causal["repeticoes"] == 3

    inconclusiva = llc.avaliar_consequencia_controlada(
        decisao=causal,
        acao_resultado={"sucesso": True, "acao": "registrar_estado_corpo", "executada": True},
        resultado_observado={"sucesso": True},
        metrica=metrica(), observacoes=observacoes()[:2],
    )
    assert inconclusiva["evidencia_causal_controlada"] is False
    assert inconclusiva["causalidade_ambiental_comprovada"] is False
    assert "repeticoes_insuficientes" in inconclusiva["erros"]

    transicao = llc.fechar_transicao(
        aprendizado_anterior=aprendizado("registrar_estado_corpo", "falha"),
        decisao=falha,
        acao_resultado={"sucesso": True, "acao": "observar_sem_atuar", "executada": False},
        resultado_observado={"sucesso": True, "estado": "resultado_observado"},
        avaliacao={"avaliacao": "sucesso", "llc2": feedback},
        aprendizado_novo={"sucesso": True, "valor": {"id": "aprendizado-novo"}},
        evidencia_causal=causal,
    )
    assert transicao["ciclo_fechado"] is True
    assert transicao["aprendizado_anterior_id"] == "aprendizado-teste"
    assert transicao["aprendizado_novo_id"] == "aprendizado-novo"
    assert transicao["causalidade_ambiental_comprovada"] is True

    contexto = llc.contexto()
    assert contexto["versao"] == "LLC.3.0.0"
    assert contexto["protocolo_causal_controlado"] is True
    assert contexto["causalidade_ambiental"] is False
    assert contexto["treinamento_automatico"] is False
    assert contexto["implantacao_automatica"] is False

    print("TESTE_LLC_LEARNING_LOOP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
