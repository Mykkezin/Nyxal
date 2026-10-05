#!/usr/bin/env python3
"""
NYXOS — LAUNCHER DO CICLO OPERACIONAL RESIDENTE M5.7

Uso explícito pelo operador local. A descoberta AE1 permanece separada
da execução experimental AE2, que só é ativada com flag explícita.
Nenhuma camada concede autorização de integração.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from nixal_runtime import NyxalRuntime
from nixal_ciclo_residente import CicloResidenteNixOS
from nixal_auto_evolucao import AutoEvolucaoGovernadaNixOS
from nixal_auto_experimento_ae2 import AutoExperimentoIsoladoAE2


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
    args = parser.parse_args()

    runtime = NyxalRuntime()
    auto_evolucao = AutoEvolucaoGovernadaNixOS(BASE_DIR)
    auto_experimento = AutoExperimentoIsoladoAE2(
        runtime,
        runtime.solicitacao_evolucao,
        habilitada=args.habilitar_auto_experimento,
    )
    residente = CicloResidenteNixOS(
        runtime,
        runtime.persistencia_operacional,
        auto_evolucao,
        auto_experimento,
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
    print("=" * 64)

    return 0 if all(
        isinstance(resultado, dict)
        and resultado.get("sucesso") is True
        for resultado in resultados
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
