#!/usr/bin/env python3
"""Decisão governada da Nyxal para bloqueios de validação CI.

Adaptador determinístico: interpreta evidências estruturadas e escolhe a próxima
ação segura. Não é uma nova engine de aprendizagem nem um executor. Não chama
serviços externos, executa comandos, altera código, faz merge ou implanta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class DecisaoAutonomaCI:
    FONTE = "decisao_autonoma_ci_nyxal"
    VERSAO = "1.0.0"
    ESTADOS_VALIDACAO = {"not_run", "passed", "failed", "unknown"}
    VALIDACOES_OBRIGATORIAS = (
        "compilacao", "politica_origem", "integracao_http", "regressoes",
    )
    INVARIANTES = {
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "stable_modificada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
        "execucao_local": False,
        "treinamento_automatico": False,
        "implantacao_automatica": False,
        "merge_automatico": False,
    }
    ACOES_PROIBIDAS = (
        "merge_main", "deploy_producao", "alterar_stable",
        "desativar_gates_de_seguranca", "publicar_credenciais",
        "executar_comando_arbitrario",
    )

    @staticmethod
    def _texto(valor: Any) -> str | None:
        return valor.strip() if isinstance(valor, str) and valor.strip() else None

    @classmethod
    def _resposta(
        cls, observacao: dict[str, Any], acao: str, motivo: str,
        passos: list[str], exige_humano: bool, bloqueio: str | None,
        evidencia: dict[str, Any],
    ) -> dict[str, Any]:
        canonico = json.dumps(
            {"observacao": observacao, "acao": acao, "evidencia": evidencia},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        return {
            "sucesso": True,
            "estado": "decisao_ci_emitida",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "decisao_id": hashlib.sha256(canonico.encode("utf-8")).hexdigest(),
            "head_sha": observacao.get("head_sha"),
            "acao_escolhida": acao,
            "motivo": motivo,
            "evidencia": evidencia,
            "proximos_passos": passos,
            "bloqueio_ate": bloqueio,
            "exige_intervencao_humana": exige_humano,
            "acoes_proibidas": list(cls.ACOES_PROIBIDAS),
            "governanca": dict(cls.INVARIANTES),
            "handoff": {
                "limite_do_escopo": "validacao_ci_seguranca_api",
                "resultado_evidencia": evidencia["classificacao_ci"],
                "aprendizado_permanente": False,
                "autoridade_de_integracao": False,
                "memoria_paralela_criada": False,
                "destino": "ciclo AE/N9/LLC existente, quando integrado pelo chamador",
            },
        }

    @classmethod
    def decidir(cls, observacao: dict[str, Any]) -> dict[str, Any]:
        """Escolhe a próxima ação usando somente evidência declarada.

        Esquema de entrada:
        {
          "head_sha": "...",
          "ci": {
            "jobs": [{"conclusion": "failure", "runner_id": 0,
                      "steps": null, "logs_available": false}],
            "repeticoes_pre_runner": 3,
            "testes_executados": false,
            "resultado_testes": "not_run"
          },
          "validacao_local": {
            "compilacao": "not_run", "politica_origem": "not_run",
            "integracao_http": "not_run", "regressoes": "not_run"
          }
        }

        Valores de estado: not_run, passed, failed, unknown. A declaração
        testes_executados só é aceita junto de evidência de etapas reais.
        """
        if not isinstance(observacao, dict):
            observacao = {}
            erro = "observacao_precisa_ser_objeto"
        else:
            erro = None

        head_sha = cls._texto(observacao.get("head_sha"))
        ci = observacao.get("ci") if isinstance(observacao.get("ci"), dict) else {}
        local = observacao.get("validacao_local") if isinstance(observacao.get("validacao_local"), dict) else {}
        jobs_raw = ci.get("jobs", [])
        if not isinstance(jobs_raw, list):
            jobs_raw = []
            erro = erro or "ci_jobs_precisa_ser_lista"
        jobs = [j for j in jobs_raw if isinstance(j, dict)]
        if len(jobs) != len(jobs_raw):
            erro = erro or "ci_job_precisa_ser_objeto"

        repeticoes = ci.get("repeticoes_pre_runner", 0)
        if isinstance(repeticoes, bool) or not isinstance(repeticoes, int) or repeticoes < 0:
            repeticoes = 0
            erro = erro or "repeticoes_pre_runner_invalidas"

        resultado_ci = ci.get("resultado_testes", "unknown")
        if resultado_ci not in cls.ESTADOS_VALIDACAO:
            resultado_ci = "unknown"
            erro = erro or "resultado_testes_ci_invalido"

        estados_locais: dict[str, str] = {}
        for nome in cls.VALIDACOES_OBRIGATORIAS:
            estado = local.get(nome, "not_run")
            if estado not in cls.ESTADOS_VALIDACAO:
                estado = "unknown"
                erro = erro or f"estado_{nome}_invalido"
            estados_locais[nome] = estado

        status_jobs = []
        for job in jobs:
            steps = job.get("steps")
            steps_vazias = steps is None or (isinstance(steps, list) and not steps)
            if steps is not None and not isinstance(steps, list):
                erro = erro or "ci_steps_precisam_ser_lista_ou_null"
            runner_nao_alocado = job.get("runner_id") == 0
            logs = job.get("logs_available") is True
            pre_runner_job = bool(
                job.get("conclusion") == "failure"
                and runner_nao_alocado and steps_vazias and not logs
            )
            status_jobs.append({
                "conclusion": job.get("conclusion", "unknown"),
                "runner_nao_alocado": runner_nao_alocado,
                "steps_ausentes": steps_vazias,
                "logs_disponiveis": logs,
                "assinatura_pre_runner": pre_runner_job,
            })

        pre_runner = bool(status_jobs) and all(j["assinatura_pre_runner"] for j in status_jobs)
        ci_executou_etapas = any(not j["steps_ausentes"] for j in status_jobs)
        testes_executados = bool(
            ci.get("testes_executados") is True and ci_executou_etapas and not pre_runner
        )
        local_falhou = any(v == "failed" for v in estados_locais.values())
        ci_falhou_com_execucao = testes_executados and resultado_ci == "failed"
        local_completo = all(v == "passed" for v in estados_locais.values())
        local_tem_evidencia = any(v in {"passed", "failed"} for v in estados_locais.values())
        ci_passou = (
            bool(status_jobs)
            and all(j["conclusion"] == "success" for j in status_jobs)
            and ci_executou_etapas and testes_executados and resultado_ci == "passed"
        )
        if pre_runner:
            classificacao = "falha_pre_runner_confirmada"
        elif ci_falhou_com_execucao:
            classificacao = "testes_falharam_apos_execucao"
        elif ci_passou:
            classificacao = "ci_passou_com_execucao_de_testes"
        else:
            classificacao = "execucao_ci_nao_confirmada"

        evidencia = {
            "classificacao_ci": classificacao,
            "quantidade_jobs_observados": len(status_jobs),
            "jobs": status_jobs,
            "repeticoes_pre_runner": repeticoes,
            "testes_ci_executados": testes_executados,
            "resultado_testes_ci": resultado_ci,
            "validacao_local": estados_locais,
            "validacao_local_completa": local_completo,
            "head_sha_presente": head_sha is not None,
            "erro_entrada": erro,
        }
        base = {**observacao, "head_sha": head_sha}

        if erro or head_sha is None:
            return cls._resposta(
                base, "coletar_evidencia_confiavel",
                "A observação é incompleta; não é seguro concluir se a falha é de código ou infraestrutura.",
                ["Corrigir o formato da observação e informar o SHA exato.",
                 "Separar status do runner, etapas executadas, resultado dos testes e disponibilidade dos logs."],
                False, "qualquer alteração de código ou promoção até evidência suficiente", evidencia,
            )

        if local_falhou or ci_falhou_com_execucao:
            logs = any(j["logs_disponiveis"] for j in status_jobs)
            passos = (
                ["Preservar o resultado e os logs da execução real.",
                 "Identificar o primeiro erro reproduzível e propor a menor correção na branch.",
                 "Reexecutar os testes afetados e as regressões."]
                if logs or local_falhou else
                ["Obter os logs de uma execução real antes de atribuir falha ao código.",
                 "Não fazer commit corretivo baseado apenas num estado failure sem etapas/logs."]
            )
            return cls._resposta(
                base, "investigar_falha_real_de_validacao",
                "Há evidência explícita de teste executado com falha; investigar o erro concreto antes de alterar o código.",
                passos, False, "merge e deploy até todos os testes obrigatórios passarem", evidencia,
            )

        if pre_runner and not local_completo:
            return cls._resposta(
                base, "executar_validacao_local_sem_editar_codigo",
                "Os jobs falharam antes do runner e não há logs; isso não demonstra regressão no código. A ação que melhor reduz a incerteza é validar localmente, congelando novas mudanças de código até haver resultados.",
                ["Executar py_compile em nixal_http_security.py e nyxal_web_api.py.",
                 "Executar teste_nixal_http_security.py.",
                 "Executar teste_api_security_auth.py (22 métodos HTTP).",
                 "Executar teste_api_chat_sem_voz.py e as regressões principais.",
                 "Anexar SHA, comandos, códigos de saída e logs como evidência."],
                True, "não alterar mais o módulo de segurança até os testes locais produzirem evidência; sem merge/deploy", evidencia,
            )

        if pre_runner and local_completo:
            if repeticoes >= 2:
                return cls._resposta(
                    base, "escalar_bloqueio_de_infraestrutura_ci",
                    "A validação local passou e pelo menos duas tentativas CI falharam antes de alocar runner. A hipótese principal é infraestrutura de CI; a causa administrativa exata não está comprovada.",
                    ["Manter a PR como rascunho e preservar a evidência de não execução.",
                     "Solicitar ao responsável da conta/GitHub Support diagnóstico de provisionamento de runner.",
                     "Não gerar commits só para forçar novas tentativas no mesmo bloqueio."],
                    True, "merge/deploy até a CI executar testes ou o operador aprovar exceção formal", evidencia,
                )
            return cls._resposta(
                base, "observar_nova_execucao_ci",
                "A validação local passou, mas a evidência de falha pré-runner ainda é insuficiente para escalada conclusiva.",
                ["Recolher uma nova execução CI sem alterar código e comparar a assinatura do job."],
                False, "merge/deploy até a CI executar testes de verdade", evidencia,
            )

        if ci_passou and local_completo:
            return cls._resposta(
                base, "solicitar_revisao_humana",
                "A CI executou os testes e as validações obrigatórias passaram; a próxima fronteira é revisão humana, não merge automático.",
                ["Anexar as evidências ao PR.", "Solicitar revisão humana do diff e dos riscos residuais."],
                True, "merge continua sendo decisão externa do operador/revisor autorizado", evidencia,
            )

        acao = "coletar_evidencia_confiavel" if not status_jobs or not local_tem_evidencia else "completar_validacoes_pendentes"
        return cls._resposta(
            base, acao,
            "A evidência está ausente ou parcial; completar somente as verificações pendentes.",
            ["Conferir o SHA exato dos artefatos testados.",
             "Distinguir o resultado dos testes do estado do runner e dos logs.",
             "Coletar apenas as verificações sem resultado confirmado."],
            False, "merge/deploy até evidência completa e revisão autorizada", evidencia,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidencia_json", type=Path, help="Arquivo JSON com evidência estruturada da CI e das validações")
    args = parser.parse_args()
    try:
        observacao = json.loads(args.evidencia_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        print(json.dumps({"sucesso": False, "estado": "evidencia_ilegivel", "motivo": type(erro).__name__}, ensure_ascii=False))
        return 2
    decisao = DecisaoAutonomaCI.decidir(observacao)
    print(json.dumps(decisao, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if decisao.get("sucesso") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
