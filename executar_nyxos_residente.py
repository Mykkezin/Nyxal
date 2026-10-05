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
from nixal_presenca_maquina import PresencaMaquinaNixOS


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
    residente = CicloResidenteNixOS(
        runtime,
        runtime.persistencia_operacional,
        auto_evolucao,
        auto_experimento,
        auto_avaliacao,
        ciclo_evolucao_ae4,
        descoberta_continua_ae5,
        coletor_dataset_dual_ae5,
        fisiologia_operacional,
        presenca_maquina,
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
    print("=" * 64)

    return 0 if all(
        isinstance(resultado, dict)
        and resultado.get("sucesso") is True
        for resultado in resultados
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
