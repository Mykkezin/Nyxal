#!/usr/bin/env python3
"""Testes determinísticos para a decisão governada da CI."""
from __future__ import annotations
from nixal_decisao_autonoma_ci import DecisaoAutonomaCI


def base() -> dict:
    return {
        "head_sha": "82ec3c8e958f1f9a9b5d758d95bba9fc618422b4",
        "ci": {
            "jobs": [{
                "run_id": 40051018117, "job_id": 120743478042,
                "conclusion": "failure", "runner_id": 0, "runner_name": "",
                "steps": None, "logs_available": False,
            }],
            "repeticoes_pre_runner": 4,
            "testes_executados": False, "resultado_testes": "not_run",
        },
        "validacao_local": {
            "compilacao": "not_run", "politica_origem": "not_run",
            "integracao_http": "not_run", "regressoes": "not_run",
        },
    }


def testar_pre_runner_decide_validacao_local_sem_edicao() -> None:
    r = DecisaoAutonomaCI.decidir(base())
    assert r["acao_escolhida"] == "executar_validacao_local_sem_editar_codigo"
    assert r["exige_intervencao_humana"] is True
    assert r["evidencia"]["classificacao_ci"] == "falha_pre_runner_confirmada"
    assert r["governanca"]["merge_automatico"] is False
    assert r["governanca"]["implantacao_automatica"] is False


def testar_validacao_local_passou_e_pre_runner_escala_infra() -> None:
    obs = base()
    obs["validacao_local"] = {k: "passed" for k in DecisaoAutonomaCI.VALIDACOES_OBRIGATORIAS}
    r = DecisaoAutonomaCI.decidir(obs)
    assert r["acao_escolhida"] == "escalar_bloqueio_de_infraestrutura_ci"
    assert r["exige_intervencao_humana"] is True
    assert "billing" not in r["motivo"].lower()


def testar_falha_de_teste_real_leva_a_investigacao() -> None:
    obs = base()
    obs["ci"]["jobs"][0].update({"runner_id": 123, "steps": [{"name": "tests"}], "logs_available": True})
    obs["ci"].update({"testes_executados": True, "resultado_testes": "failed"})
    r = DecisaoAutonomaCI.decidir(obs)
    assert r["acao_escolhida"] == "investigar_falha_real_de_validacao"
    assert r["evidencia"]["classificacao_ci"] == "testes_falharam_apos_execucao"


def testar_ci_passou_e_so_pede_revisao_humana() -> None:
    obs = base()
    obs["ci"]["jobs"][0].update({"conclusion": "success", "runner_id": 123, "steps": [{"name": "tests"}], "logs_available": True})
    obs["ci"].update({"testes_executados": True, "resultado_testes": "passed"})
    obs["validacao_local"] = {k: "passed" for k in DecisaoAutonomaCI.VALIDACOES_OBRIGATORIAS}
    r = DecisaoAutonomaCI.decidir(obs)
    assert r["acao_escolhida"] == "solicitar_revisao_humana"
    assert r["governanca"]["merge_automatico"] is False


def testar_steps_vazias_nao_contam_como_teste_executado() -> None:
    obs = base()
    obs["ci"].update({"testes_executados": True, "resultado_testes": "failed"})
    r = DecisaoAutonomaCI.decidir(obs)
    assert r["acao_escolhida"] == "executar_validacao_local_sem_editar_codigo"
    assert r["evidencia"]["classificacao_ci"] == "falha_pre_runner_confirmada"


def testar_evidencia_invalida_falha_fechada() -> None:
    obs = base()
    obs["head_sha"] = " "
    r = DecisaoAutonomaCI.decidir(obs)
    assert r["acao_escolhida"] == "coletar_evidencia_confiavel"
    assert r["governanca"]["autorizacao_explicita"] is False


def testar_runner_id_ausente_nao_prova_pre_runner() -> None:
    obs = base()
    obs["ci"]["jobs"][0].pop("runner_id")
    r = DecisaoAutonomaCI.decidir(obs)
    assert r["evidencia"]["classificacao_ci"] == "execucao_ci_nao_confirmada"
    assert r["acao_escolhida"] == "coletar_evidencia_confiavel"


def testar_id_decisao_deterministico() -> None:
    obs = base()
    assert DecisaoAutonomaCI.decidir(obs)["decisao_id"] == DecisaoAutonomaCI.decidir(obs)["decisao_id"]


def main() -> int:
    testar_pre_runner_decide_validacao_local_sem_edicao()
    testar_validacao_local_passou_e_pre_runner_escala_infra()
    testar_falha_de_teste_real_leva_a_investigacao()
    testar_ci_passou_e_so_pede_revisao_humana()
    testar_steps_vazias_nao_contam_como_teste_executado()
    testar_evidencia_invalida_falha_fechada()
    testar_runner_id_ausente_nao_prova_pre_runner()
    testar_id_decisao_deterministico()
    print("TESTE_DECISAO_AUTONOMA_CI_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
