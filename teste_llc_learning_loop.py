#!/usr/bin/env python3
"""Teste deterministico do LLC / primeira etapa causal."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_aprendizado_persistente import AprendizadoPersistenteNixal
from nixal_learning_loop_causal import LearningLoopCausalNixal
from nixal_runtime import NyxalRuntime


def prioridades():
    return {
        "sucesso": True,
        "quantidade": 1,
        "selecionada": {
            "necessidade": "estabilidade",
            "prioridade": "alta",
        },
    }


def estado():
    return {
        "corpo": {
            "cpu": {"uso_percentual": 20.0, "estado": "normal"},
            "memoria": {"uso_percentual": 40.0, "estado": "normal"},
        }
    }


def aprendizado(acao: str, avaliacao: str) -> dict:
    return {
        "disponivel": True,
        "aprendizado_id": "aprendizado-teste",
        "ciclo_origem": "ciclo-anterior",
        "experiencia_anterior": {
            "acao": acao,
            "resultado": "resultado_observado",
        },
        "avaliacao_anterior": {
            "avaliacao": avaliacao,
        },
        "aplicado_no_ciclo_atual": True,
        "conhecimento_permanente": False,
        "arquitetura_modificada": False,
    }


def main() -> int:
    llc = LearningLoopCausalNixal()

    sem = llc.selecionar(
        estado_corpo=estado(),
        prioridades=prioridades(),
        aprendizado_anterior=None,
    )
    assert sem["acao"] == "registrar_estado_corpo"
    assert sem["llc"]["influencia_decisoria_comprovada"] is False

    falha = llc.selecionar(
        estado_corpo=estado(),
        prioridades=prioridades(),
        aprendizado_anterior=aprendizado(
            "registrar_estado_corpo",
            "falha",
        ),
    )
    assert falha["acao"] == "observar_sem_atuar"
    assert falha["llc"]["mudou_escolha"] is True
    assert falha["llc"]["influencia_decisoria_comprovada"] is True
    assert falha["llc"]["causalidade_ambiental_comprovada"] is False

    sucesso = llc.selecionar(
        estado_corpo=estado(),
        prioridades=prioridades(),
        aprendizado_anterior=aprendizado(
            "registrar_estado_corpo",
            "sucesso",
        ),
    )
    assert sucesso["acao"] == "registrar_estado_corpo"
    assert sucesso["llc"]["mudou_escolha"] is False
    assert sucesso["llc"]["influencia_decisoria_comprovada"] is False

    invalido = llc.selecionar(
        estado_corpo=estado(),
        prioridades=prioridades(),
        aprendizado_anterior={
            "disponivel": True,
            "experiencia_anterior": {"acao": "acao_desconhecida"},
            "avaliacao_anterior": {"avaliacao": "sucesso"},
            "aplicado_no_ciclo_atual": True,
        },
    )
    assert invalido["acao"] == "registrar_estado_corpo"
    assert invalido["llc"]["sinal_valido"] is False

    with TemporaryDirectory() as tmp:
        runtime = NyxalRuntime(
            arquivo_estado=Path(tmp) / "runtime.json",
            arquivo_log=Path(tmp) / "log.json",
            arquivo_memoria_aprendizado=Path(tmp) / "aprendizado.json",
            learning_loop_causal=llc,
        )
        decisao = runtime._decidir(
            estado_corpo=estado(),
            prioridades=prioridades(),
            aprendizado_anterior=aprendizado(
                "registrar_estado_corpo",
                "falha",
            ),
        )
        assert decisao["acao"] == "observar_sem_atuar"
        assert decisao["llc"]["influencia_decisoria_comprovada"] is True

        acao = runtime._agir(
            decisao=decisao,
            estado_corpo=estado(),
        )
        assert acao["sucesso"] is True
        assert acao["acao"] == "observar_sem_atuar"
        assert acao["executada"] is False

    contexto = llc.contexto()
    assert contexto["influencia_decisoria"] is True
    assert contexto["causalidade_ambiental"] is False
    assert contexto["treinamento_automatico"] is False
    assert contexto["implantacao_automatica"] is False

    print("TESTE_LLC_LEARNING_LOOP_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
