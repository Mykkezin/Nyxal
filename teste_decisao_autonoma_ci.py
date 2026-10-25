#!/usr/bin/env python3
"""Testes determinísticos para a decisão governada da CI."""
from __future__ import annotations
from nixal_decisao_autonoma_ci import DecisaoAutonomaCI
from nixal_evidencia_ci import construir_evidencia_ci


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


def testar_falha_de_compilacao_nao_e_rotulada_como_falha_de_teste() -> None:
    evidence = construir_evidencia_ci(
        head_sha="abc123",
        job_outcome="failure",
        step_outcomes={
            "compilacao": "failure",
            "politica_origem": "skipped",
            "integracao_http": "skipped",
            "decisor": "skipped",
            "shell_syntax": "skipped",
            "regressoes": "skipped",
        },
    )
    ci = evidence["ci"]
    assert ci["resultado_pipeline"] == "failed"
    assert ci["testes_executados"] is False
    assert ci["resultado_testes"] == "not_run"
    assert [item["name"] for item in ci["jobs"][0]["steps"]] == ["compilacao"]
    decision = DecisaoAutonomaCI.decidir(evidence)
    assert decision["acao_escolhida"] == "investigar_falha_de_compilacao"
    assert "não classificar isso como falha de teste" in decision["motivo"].lower()


def testar_falha_de_suite_e_separada_do_pipeline() -> None:
    evidence = construir_evidencia_ci(
        head_sha="def456",
        job_outcome="failure",
        step_outcomes={
            "compilacao": "success",
            "politica_origem": "success",
            "integracao_http": "failure",
            "decisor": "skipped",
            "shell_syntax": "skipped",
            "regressoes": "skipped",
        },
    )
    ci = evidence["ci"]
    assert ci["resultado_pipeline"] == "failed"
    assert ci["testes_executados"] is True
    assert ci["resultado_testes"] == "failed"
    decision = DecisaoAutonomaCI.decidir(evidence)
    assert decision["acao_escolhida"] == "investigar_falha_real_de_validacao"
    assert "há evidência de falha em uma suíte de teste executada" in decision["motivo"].lower()


def testar_tests_passam_mas_shell_falha() -> None:
    evidence = construir_evidencia_ci(
        head_sha="ghi789",
        job_outcome="failure",
        step_outcomes={
            "compilacao": "success",
            "politica_origem": "success",
            "integracao_http": "success",
            "decisor": "success",
            "shell_syntax": "failure",
            "regressoes": "success",
        },
    )
    ci = evidence["ci"]
    assert ci["resultado_pipeline"] == "failed"
    assert ci["testes_executados"] is True
    assert ci["resultado_testes"] == "passed"
    decision = DecisaoAutonomaCI.decidir(evidence)
    assert decision["acao_escolhida"] == "investigar_falha_de_etapa_do_pipeline"
    assert decision["evidencia"]["resultado_pipeline_ci"] == "failed"
    assert decision["evidencia"]["resultado_testes_ci"] == "passed"
    assert "não há evidência de falha numa suíte de testes executada" in decision["motivo"].lower()


def main() -> int:
    testar_pre_runner_decide_validacao_local_sem_edicao()
    testar_validacao_local_passou_e_pre_runner_escala_infra()
    testar_falha_de_teste_real_leva_a_investigacao()
    testar_ci_passou_e_so_pede_revisao_humana()
    testar_steps_vazias_nao_contam_como_teste_executado()
    testar_evidencia_invalida_falha_fechada()
    testar_runner_id_ausente_nao_prova_pre_runner()
    testar_id_decisao_deterministico()
    testar_falha_de_compilacao_nao_e_rotulada_como_falha_de_teste()
    testar_falha_de_suite_e_separada_do_pipeline()
    testar_tests_passam_mas_shell_falha()
    print("TESTE_DECISAO_AUTONOMA_CI_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
