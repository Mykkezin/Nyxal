"""Montagem factual da evidência CI, separada da política decisória.

Este módulo não classifica uma falha de compilação como falha de teste e pode
ser importado mesmo quando o módulo de decisão está sendo validado.
"""
from __future__ import annotations

from typing import Any


ETAPAS_CI = (
    "compilacao",
    "politica_origem",
    "integracao_http",
    "decisor",
    "shell_syntax",
    "regressoes",
)
ETAPAS_DE_TESTE = (
    "politica_origem",
    "integracao_http",
    "decisor",
    "regressoes",
)
ESTADOS_RAW = frozenset({"success", "failure", "skipped", "cancelled"})
ESTADOS_NORMALIZADOS = {
    "success": "passed",
    "failure": "failed",
    "skipped": "not_run",
    "cancelled": "not_run",
    "unknown": "unknown",
}


def construir_evidencia_ci(
    *,
    head_sha: str,
    job_outcome: str,
    step_outcomes: dict[str, str],
) -> dict[str, Any]:
    """Build truthful evidence separating test verdict from pipeline verdict.

    A compilation or shell failure can end the workflow before all test suites
    run. In that case, resultado_testes remains not_run/unknown, not failed.
    """
    normalized: dict[str, str] = {}
    for step in ETAPAS_CI:
        value = step_outcomes.get(step, "unknown")
        normalized[step] = value if isinstance(value, str) and value in ESTADOS_RAW else "unknown"

    test_outcomes = {key: normalized[key] for key in ETAPAS_DE_TESTE}
    tests_executed = any(value in {"success", "failure"} for value in test_outcomes.values())
    if any(value == "failure" for value in test_outcomes.values()):
        test_result = "failed"
    elif all(value == "success" for value in test_outcomes.values()):
        test_result = "passed"
    elif not tests_executed:
        test_result = "not_run"
    else:
        test_result = "unknown"

    job_status = job_outcome if isinstance(job_outcome, str) and job_outcome in {"success", "failure", "cancelled"} else "unknown"
    if job_status == "failure" or any(value == "failure" for value in normalized.values()):
        pipeline_result = "failed"
    elif job_status == "success" and all(value == "success" for value in normalized.values()):
        pipeline_result = "passed"
    else:
        pipeline_result = "unknown"

    executed_steps = [
        {"name": name, "outcome": outcome}
        for name, outcome in normalized.items()
        if outcome in {"success", "failure"}
    ]
    local_validation = {
        name: ESTADOS_NORMALIZADOS[normalized[name]]
        for name in ("compilacao", "politica_origem", "integracao_http", "regressoes")
    }

    return {
        "head_sha": head_sha.strip() if isinstance(head_sha, str) else "",
        "ci": {
            "jobs": [{
                "conclusion": job_status,
                "steps": executed_steps,
                "logs_available": bool(executed_steps),
            }],
            # The running job cannot discover the cumulative history of other runs.
            # This zero is scoped to the current run, not a claim about past attempts.
            "repeticoes_pre_runner": 0,
            "repeticoes_pre_runner_escopo": "execucao_atual_apenas",
            "testes_executados": tests_executed,
            "resultado_testes": test_result,
            "resultado_pipeline": pipeline_result,
        },
        "validacao_local": local_validation,
    }
