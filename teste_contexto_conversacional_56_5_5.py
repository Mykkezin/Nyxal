#!/usr/bin/env python3

"""
NIXAL — TESTE DO CONTEXTO CONVERSACIONAL

Microetapa 56.5.5

Valida:
    memória volátil por sessão
        +
    diálogo contextual
        +
    integração do núcleo conversacional.

Nenhum modelo real é consultado.
"""

from __future__ import annotations

import sys
import types


# A suíte não precisa de Ollama nem das dependências do catálogo de capacidades.
# Os contratos-base usados pelo núcleo são substituídos por dublês locais.
agente_modulo = types.ModuleType("nixal_agente_qwen")
compositor_modulo = types.ModuleType("nixal_composicao_56_3_9")
dialogo_modulo = types.ModuleType("nixal_dialogo_qwen")


class AgenteNixalQwenStub:
    def __init__(self) -> None:
        self.capacidades = types.SimpleNamespace(
            listar_capacidades=lambda: []
        )


class CompositorNixalStub:
    def obter_contexto_dominio(self, _texto: str) -> dict:
        return {"capacidades_prioritarias": []}


class DialogoQwenNixalStub:
    FONTE = "dialogo_qwen_nixal"
    VERSAO = "56.5.5"


agente_modulo.AgenteNixalQwen = AgenteNixalQwenStub
compositor_modulo.CompositorNixal = CompositorNixalStub
dialogo_modulo.DialogoQwenNixal = DialogoQwenNixalStub

sys.modules["nixal_agente_qwen"] = agente_modulo
sys.modules["nixal_composicao_56_3_9"] = compositor_modulo
sys.modules["nixal_dialogo_qwen"] = dialogo_modulo


from nixal_gerenciador_sessoes import GerenciadorSessoesNixal
from nixal_interface import InterfaceConversacionalNixal
from nixal_integracao_sessao_transporte import (
    IntegracaoSessaoTransporteNixal,
)
from nixal_memoria_conversacional import (
    MemoriaConversacionalNixal,
)
from nixal_nucleo_conversacional import (
    NucleoConversacionalNixal,
)
from nixal_transporte_conversacional import (
    TransporteConversacionalNixal,
)

class AgenteSemCapacidade(AgenteNixalQwenStub):
    def atender(self, necessidade: str) -> dict:
        return {
            "atendida": False,
            "necessidade": necessidade,
            "capacidade_escolhida": None,
            "argumentos": {},
            "selecao": {
                "sucesso": True,
                "capacidade": None,
                "argumentos": {},
                "candidatos": [],
                "tentativa_correcao": False,
                "erro": None,
                "motivo": "abstencao",
            },
            "resultado": None,
        }


class DialogoFake(DialogoQwenNixalStub):
    def __init__(self) -> None:
        self.chamadas = []

    def responder(
        self,
        texto: str,
        historico=None,
    ) -> dict:
        historico_copiado = list(historico or [])
        self.chamadas.append(
            {
                "texto": texto,
                "historico": historico_copiado,
            }
        )

        quantidade = len(historico_copiado)
        return {
            "sucesso": True,
            "estado": "resposta_gerada",
            "origem": self.FONTE,
            "resposta": (
                f"Recebi '{texto}'. "
                f"Histórico anterior: {quantidade} mensagens."
            ),
            "modelo": "fake",
            "mensagens_consideradas": quantidade + 1,
            "permanente": False,
            "versao_dialogo": self.VERSAO,
        }


def verificar(
    condicao: bool,
    mensagem: str,
    falhas: list[str],
    total: list[int],
) -> None:
    total[0] += 1
    print(
        f"[{'PASS' if condicao else 'FAIL'}] "
        f"{total[0]}. {mensagem}"
    )
    if not condicao:
        falhas.append(mensagem)


def main() -> None:
    falhas: list[str] = []
    total = [0]

    memoria = MemoriaConversacionalNixal(max_mensagens=4)

    verificar(
        memoria.VERSAO == "56.5.5",
        "versão da memória é 56.5.5",
        falhas,
        total,
    )

    for indice in range(6):
        memoria.registrar(
            "s1",
            "user" if indice % 2 == 0 else "assistant",
            f"mensagem-{indice}",
        )

    contexto = memoria.obter("s1")

    verificar(
        contexto["sucesso"] is True,
        "contexto pode ser consultado",
        falhas,
        total,
    )

    verificar(
        contexto["quantidade"] == 4,
        "janela máxima de mensagens é respeitada",
        falhas,
        total,
    )

    verificar(
        [item["texto"] for item in contexto["mensagens"]]
        == ["mensagem-2", "mensagem-3", "mensagem-4", "mensagem-5"],
        "somente as mensagens mais recentes permanecem",
        falhas,
        total,
    )

    verificar(
        memoria.obter("s2")["quantidade"] == 0,
        "sessões possuem contextos separados",
        falhas,
        total,
    )

    copia = contexto["mensagens"]
    copia[0]["texto"] = "mutado"

    verificar(
        memoria.obter("s1")["mensagens"][0]["texto"] == "mensagem-2",
        "resultado da memória permanece isolado",
        falhas,
        total,
    )

    limpar = memoria.limpar("s1")

    verificar(
        limpar["sucesso"] is True,
        "contexto pode ser limpo explicitamente",
        falhas,
        total,
    )

    verificar(
        memoria.obter("s1")["quantidade"] == 0,
        "limpeza remove o contexto volátil da sessão",
        falhas,
        total,
    )

    dialogo = DialogoFake()
    agente = AgenteSemCapacidade()
    nucleo = NucleoConversacionalNixal(
        interface=InterfaceConversacionalNixal(),
        agente=agente,
        compositor=CompositorNixalStub(),
        memoria_conversacional=MemoriaConversacionalNixal(
            max_mensagens=8
        ),
        dialogo=dialogo,
    )

    sessoes = GerenciadorSessoesNixal()
    transporte = TransporteConversacionalNixal()
    integracao = IntegracaoSessaoTransporteNixal(
        transporte=transporte,
        sessoes=sessoes,
    )

    primeira = integracao.processar_mensagem(
        texto="Olá, Nyxal.",
        nucleo=nucleo,
    )

    sessao = primeira.get("sessao")

    primeira_sucesso = primeira.get("sucesso") is True

    verificar(
        primeira_sucesso,
        "primeira mensagem é processada",
        falhas,
        total,
    )

    verificar(
        isinstance(sessao, str) and bool(sessao),
        "primeira mensagem recebe uma sessão",
        falhas,
        total,
    )

    if not primeira_sucesso:
        import json

        print(
            "DIAGNOSTICO_PRIMEIRA_MENSAGEM="
            + json.dumps(
                primeira,
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1)

    resposta_1 = (
        primeira["valor"]["transporte"]["resposta"]["resposta"]
    )

    verificar(
        "Olá, Nyxal." in resposta_1,
        "primeira resposta usa o módulo de diálogo",
        falhas,
        total,
    )

    segunda = integracao.processar_mensagem(
        texto="Você lembra de mim?",
        nucleo=nucleo,
        sessao_id=sessao,
    )

    verificar(
        segunda["sucesso"] is True,
        "segunda mensagem reutiliza a sessão",
        falhas,
        total,
    )

    verificar(
        len(dialogo.chamadas) == 2,
        "módulo de diálogo foi chamado duas vezes",
        falhas,
        total,
    )

    historico_segundo_turno = dialogo.chamadas[1]["historico"]

    verificar(
        historico_segundo_turno
        == [
            {
                "papel": "user",
                "texto": "Olá, Nyxal.",
            },
            {
                "papel": "assistant",
                "texto": resposta_1,
            },
        ],
        "segundo turno recebe o histórico anterior",
        falhas,
        total,
    )

    verificar(
        len(nucleo.memoria_conversacional.obter(sessao)["mensagens"])
        == 4,
        "usuário e assistente são registrados na mesma sessão",
        falhas,
        total,
    )

    verificar(
        nucleo.memoria_conversacional.obter(sessao)["permanente"] is False,
        "contexto não é conhecimento permanente",
        falhas,
        total,
    )

    encerramento = integracao.encerrar_sessao(sessao)

    verificar(
        encerramento["sucesso"] is True,
        "sessão pode ser encerrada após conversar",
        falhas,
        total,
    )

    rejeitada = integracao.processar_mensagem(
        texto="mensagem depois do fechamento",
        nucleo=nucleo,
        sessao_id=sessao,
    )

    verificar(
        rejeitada["sucesso"] is False
        and rejeitada["estado"] == "sessao_inativa",
        "sessão encerrada não aceita nova mensagem",
        falhas,
        total,
    )

    print()
    print("=" * 64)
    print("TESTE — CONTEXTO CONVERSACIONAL 56.5.5")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {total[0]}")
    print(f"FALHAS: {len(falhas)}")
    print(f"PASSOU: {not falhas}")
    print("=" * 64)

    if falhas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
