#!/usr/bin/env python3

"""
NIXAL — AGENTE DE CAPACIDADES

Microetapa 53.1

Objetivo:
Permitir que a Nixal receba uma necessidade simples,
identifique a capacidade adequada e execute essa capacidade.

Nesta etapa:
- não existe execução arbitrária de código
- não existe shell
- não existe controle de hardware
- somente capacidades previamente registradas podem ser usadas
- a seleção é determinística
- necessidades sem capacidade conhecida são recusadas

Fluxo:

necessidade
    ↓
identificação da intenção
    ↓
seleção de capacidade
    ↓
execução
    ↓
resultado
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from nixal_capacidades import GerenciadorCapacidades


class AgenteNixal:

    def __init__(self) -> None:

        self.capacidades = GerenciadorCapacidades()

    # ============================================================
    # DESCOBERTA
    # ============================================================

    def descobrir_capacidades(self) -> list[dict[str, str]]:

        return self.capacidades.listar_capacidades()

    # ============================================================
    # SELEÇÃO
    # ============================================================

    def selecionar_capacidade(
        self,
        necessidade: str,
    ) -> str | None:

        texto = necessidade.lower().strip()

        # ========================================================
        # 1. MEMÓRIA CORPORAL
        #
        # Deve vir antes da capacidade do corpo porque expressões
        # como "eventos do meu corpo" contêm a palavra "corpo".
        # ========================================================

        if any(
            palavra in texto
            for palavra in [
                "eventos corporais",
                "evento corporal",
                "eventos do corpo",
                "evento do corpo",
                "eventos meu corpo",
                "eventos que meu corpo registrou",
                "memória corporal",
                "memoria corporal",
                "histórico corporal",
                "historico corporal",
                "histórico do corpo",
                "historico do corpo",
                "eventos registrados",
            ]
        ):

            return "ler_memoria_corporal"

        # ========================================================
        # 2. HORA
        # ========================================================

        if any(
            palavra in texto
            for palavra in [
                "hora",
                "horário",
                "horario",
                "que horas são",
                "que horas sao",
            ]
        ):

            return "obter_hora"

        # ========================================================
        # 3. ARQUIVOS
        # ========================================================

        if any(
            palavra in texto
            for palavra in [
                "arquivo",
                "arquivos",
                "ficheiro",
                "ficheiros",
                "arquivos do projeto",
                "arquivos do sistema",
            ]
        ):

            return "listar_arquivos"

        # ========================================================
        # 4. CORPO
        #
        # Aqui ficam informações que a Nixal realmente consegue
        # observar no corpo que foi construído até agora.
        # ========================================================

        indicadores_corporais = [
            "meu corpo",
            "estado do corpo",
            "como está meu corpo",
            "como esta meu corpo",
            "cpu",
            "processador",
            "ram",
            "memória do computador",
            "memoria do computador",
            "gpu",
            "placa de vídeo",
            "placa de video",
            "temperatura da cpu",
            "temperatura do cpu",
            "temperatura da gpu",
            "temperatura do computador",
            "temperaturas do computador",
            "temperaturas do corpo",
            "temperatura do corpo",
            "uso da cpu",
            "uso da gpu",
            "uso de memória",
            "uso de memoria",
            "armazenamento",
            "disco",
            "processos",
            "carga da cpu",
            "carga do processador",
        ]

        # ========================================================
        # 5. REJEIÇÃO EXPLÍCITA DE ALVOS AINDA NÃO DISPONÍVEIS
        #
        # "temperatura do mundo" não deve ser confundida com uma
        # temperatura corporal simplesmente porque contém
        # "temperatura".
        # ========================================================

        alvos_desconhecidos = [
            "temperatura do mundo",
            "temperatura do ambiente",
            "temperatura lá fora",
            "temperatura la fora",
            "clima",
            "tempo lá fora",
            "tempo la fora",
            "temperatura externa",
            "temperatura da rua",
            "temperatura da cidade",
        ]

        if any(
            alvo in texto
            for alvo in alvos_desconhecidos
        ):

            return None

        if any(
            indicador in texto
            for indicador in indicadores_corporais
        ):

            return "ler_estado_corpo"

        # ========================================================
        # 6. NENHUMA CAPACIDADE CONHECIDA
        # ========================================================

        return None

    # ============================================================
    # EXECUÇÃO ORIENTADA POR NECESSIDADE
    # ============================================================

    def atender(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        capacidade = self.selecionar_capacidade(
            necessidade
        )

        # --------------------------------------------------------
        # Nenhuma capacidade encontrada
        # --------------------------------------------------------

        if capacidade is None:

            return {
                "atendida": False,
                "necessidade": necessidade,
                "capacidade_escolhida": None,
                "resultado": None,
                "motivo": (
                    "Nenhuma capacidade conhecida "
                    "foi considerada adequada."
                ),
            }

        # --------------------------------------------------------
        # Executa a capacidade
        # --------------------------------------------------------

        resultado = self.capacidades.executar(
            capacidade
        )

        return {
            "atendida": resultado.sucesso,
            "necessidade": necessidade,
            "capacidade_escolhida": capacidade,
            "resultado": asdict(resultado),
        }

    # ============================================================
    # EXIBIÇÃO
    # ============================================================

    def mostrar_capacidades(self) -> None:

        print()
        print("=" * 60)
        print("CAPACIDADES CONHECIDAS PELA NIXAL")
        print("=" * 60)

        capacidades = self.descobrir_capacidades()

        for capacidade in capacidades:

            print(
                f"- {capacidade['nome']}: "
                f"{capacidade['descricao']}"
            )

        print()

    def mostrar_atendimento(
        self,
        necessidade: str,
    ) -> None:

        resultado = self.atender(
            necessidade
        )

        print()
        print("-" * 60)
        print(
            f"NECESSIDADE: {necessidade}"
        )
        print("-" * 60)

        print(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
            )
        )


# ================================================================
# TESTE
# ================================================================

def main() -> None:

    agente = AgenteNixal()

    print()
    print("=" * 60)
    print("NIXAL — AGENTE DE CAPACIDADES")
    print("=" * 60)

    agente.mostrar_capacidades()

    # ------------------------------------------------------------
    # Teste 1 — hora
    # ------------------------------------------------------------

    agente.mostrar_atendimento(
        "Preciso saber a hora."
    )

    # ------------------------------------------------------------
    # Teste 2 — corpo
    # ------------------------------------------------------------

    agente.mostrar_atendimento(
        "Preciso verificar como está meu corpo."
    )

    # ------------------------------------------------------------
    # Teste 3 — memória corporal
    # ------------------------------------------------------------

    agente.mostrar_atendimento(
        "Quero saber quais eventos meu corpo registrou."
    )

    # ------------------------------------------------------------
    # Teste 4 — arquivos
    # ------------------------------------------------------------

    agente.mostrar_atendimento(
        "Quero conhecer os arquivos do projeto."
    )

    # ------------------------------------------------------------
    # Teste 5 — necessidade ainda não disponível
    # ------------------------------------------------------------

    agente.mostrar_atendimento(
        "Preciso descobrir a temperatura do mundo."
    )

    print()
    print("=" * 60)
    print("MICROETAPA 53.1 FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
