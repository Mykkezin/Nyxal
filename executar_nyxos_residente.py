#!/usr/bin/env python3
"""
NYXOS — LAUNCHER DO CICLO OPERACIONAL RESIDENTE M5.7

Uso explícito pelo operador local. A descoberta AE1 permanece separada
da execução experimental AE2, que só é ativada com flag explícita.
AE4 orquestra AE1→AE2→AE3 sem conceder autorização de integração.
Nenhuma camada concede autoridade de integração.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from nixal_runtime import NyxalRuntime
from nixal_ciclo_residente import CicloResidenteNixOS
from nixal_auto_evolucao import AutoEvolucaoGovernadaNixOS
from nixal_auto_experimento_ae2 import AutoExperimentoIsoladoAE2
from nixal_auto_avaliacao_ae3 import AutoAvaliacaoAE3
from nixal_ciclo_evolucao_ae4 import CicloEvolucaoResidenteAE4
from nixal_descoberta_continua_ae5 import DescobertaContinuaGovernadaAE5
from nixal_coletor_dataset_dual_ae5 import ColetorDatasetDualAE5
from nixal_solicitacao_evolucao import SolicitacaoEvolucaoNixal
from nixal_fisiologia_operacional import FisiologiaOperacionalNixOS
from nixal_gateway_atuacao import GatewayAtuacaoNixOS
from nixal_adaptador_host_controlado import AdaptadorHostControladoNixOS
from nixal_adaptador_sandbox_fisico import AdaptadorSandboxFisicoNixOS
from nixal_auditoria_atuacao import AuditoriaAtuacaoNixOS
from nixal_plano_central_controle import PlanoCentralControleNixOS
from nixal_presenca_maquina import PresencaMaquinaNixOS
from nixal_autoreparo_residente import AutoreparoResidenteNixOS


BASE_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa o ciclo operacional residente do NyxOS."
    )
    parser.add_argument(
        "--max-ciclos",
        type=int,
        default=None,
        help="Quantidade de ciclos da sessão. Sem valor, executa continuamente.",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=5.0,
        help="Intervalo em segundos entre ciclos.",
    )
    parser.add_argument(
        "--continuar-em-erro",
        action="store_true",
        help="Não interrompe a residência quando um ciclo falhar.",
    )
    parser.add_argument(
        "--habilitar-aprendizado",
        action="store_true",
        help=(
            "Habilita explicitamente a persistência de aprendizado no residente. "
            "Desabilitado por padrão para impedir aprendizado contínuo sem supervisão."
        ),
    )
    parser.add_argument(
        "--habilitar-auto-experimento",
        action="store_true",
        help=(
            "Ativa AE2 para processar automaticamente, no máximo uma por ciclo, "
            "solicitação formal já pronta para experimento remoto."
        ),
    )
    parser.add_argument(
        "--habilitar-ae5-descoberta",
        action="store_true",
        help="Ativa explicitamente a descoberta contínua governada de valor econômico.",
    )
    args = parser.parse_args()

    solicitacao_evolucao = SolicitacaoEvolucaoNixal(repositorio=BASE_DIR)
    runtime = NyxalRuntime(
        solicitacao_evolucao=solicitacao_evolucao,
        modo_residente=True,
        aprendizado_habilitado=args.habilitar_aprendizado,
    )
    auto_evolucao = AutoEvolucaoGovernadaNixOS(BASE_DIR)
    auto_experimento = AutoExperimentoIsoladoAE2(
        runtime,
        runtime.solicitacao_evolucao,
        habilitada=args.habilitar_auto_experimento,
    )
    auto_avaliacao = AutoAvaliacaoAE3()
    ciclo_evolucao_ae4 = CicloEvolucaoResidenteAE4(
        auto_evolucao,
        auto_experimento,
        auto_avaliacao,
        repositorio=BASE_DIR,
    )
    descoberta_continua_ae5 = DescobertaContinuaGovernadaAE5(
        repositorio=BASE_DIR,
        habilitada=args.habilitar_ae5_descoberta,
    )
    coletor_dataset_dual_ae5 = ColetorDatasetDualAE5(
        repositorio=BASE_DIR,
        habilitada=args.habilitar_ae5_descoberta,
    )
    fisiologia_operacional = FisiologiaOperacionalNixOS(
        intervalo_esperado_segundos=args.intervalo,
        arquivo=BASE_DIR / "fisiologia_operacional_nyxos.json",
        delta_nyxos=runtime.delta_nyxos,
    )
    presenca_maquina = PresencaMaquinaNixOS(
        arquivo=BASE_DIR / "presenca_maquina_nyxos.json",
    )
    autoreparo_residente = AutoreparoResidenteNixOS()
    plano_central_controle = PlanoCentralControleNixOS(
        arquivo=BASE_DIR / "plano_central_controle_nyxos.json",
    )
    auditoria_atuacao = AuditoriaAtuacaoNixOS(
        arquivo=BASE_DIR / "auditoria_atuacao_nyxos.jsonl",
    )
    sandbox_fisico = AdaptadorSandboxFisicoNixOS(
        diretorio_sandbox=BASE_DIR / "sandbox_nyxos",
        habilitada=False,
        auditoria=auditoria_atuacao,
    )
    gateway_atuacao = GatewayAtuacaoNixOS(
        arquivo=BASE_DIR / "gateway_atuacao_nyxos.json",
        executor=sandbox_fisico,
        auditoria=auditoria_atuacao,
        execucao_fisica_habilitada=False,
    )
    residente = CicloResidenteNixOS(
        runtime,
        runtime.persistencia_operacional,
        auto_evolucao,
        auto_experimento,
        auto_avaliacao,
        ciclo_evolucao_ae4,
        descoberta_continua_ae5,
        fisiologia_operacional,
        presenca_maquina,
        plano_central_controle,
        gateway_atuacao,
        coletor_dataset_dual_ae5=coletor_dataset_dual_ae5,
        autoreparo_residente=autoreparo_residente,
        intervalo_segundos=args.intervalo,
        parar_em_erro=not args.continuar_em_erro,
    )

    resultados = residente.executar(
        max_ciclos=args.max_ciclos
    )

    contexto = residente.contexto()

    print("=" * 64)
    print("NYXOS — CICLO RESIDENTE M5.7")
    print("=" * 64)
    print(f"CICLOS NESTA SESSÃO: {len(resultados)}")
    print(f"CICLOS TOTAIS: {contexto['ciclos_executados']}")
    print(f"ESTADO: {contexto['estado_residente']}")
    print(
        "AE1 — DESCOBERTA: "
        + (
            "HABILITADA"
            if contexto["auto_evolution_habilitada"]
            else "DESABILITADA"
        )
    )
    print(
        "AE2 — EXECUÇÃO EXPERIMENTAL: "
        + (
            "HABILITADA"
            if contexto["auto_experimento_ae2_habilitado"]
            else "DESABILITADA"
        )
    )
    print("AE3 — AVALIAÇÃO: HABILITADA")
    print("AE4 — CICLO DE EVOLUÇÃO: " + ("HABILITADO" if contexto["ciclo_evolucao_ae4_habilitado"] else "DESABILITADO"))
    print("AE5 — DESCOBERTA CONTÍNUA: " + ("HABILITADA" if contexto["descoberta_continua_ae5_habilitada"] else "DESABILITADA"))
    print("AE5 — DATASETS DUAIS: " + ("HABILITADOS" if contexto["coleta_dataset_dual_ae5_habilitada"] else "DESABILITADOS"))
    print("M5.15 — GATEWAY DE ATUAÇÃO: " + ("HABILITADO" if contexto["gateway_atuacao_habilitado"] else "DESABILITADO"))
    print("M5.15 — EXECUÇÃO FÍSICA: " + ("HABILITADA" if contexto["execucao_fisica_habilitada"] else "DESABILITADA"))
    print("M5.16 — ADAPTADOR HOST: CONTROLADO / SOMENTE LEITURA")
    print("M5.17 — SANDBOX FÍSICO: DISPONÍVEL / DESABILITADO")
    print("M5.18 — AUDITORIA DE ATUAÇÃO: HABILITADA")
    print("M5.25 — AUTOREPARO API/DESKTOP: HABILITADO")
    print("=" * 64)

    return 0 if all(
        isinstance(resultado, dict)
        and resultado.get("sucesso") is True
        for resultado in resultados
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
