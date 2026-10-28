#!/usr/bin/env python3

"""
NIXAL — TESTE DE INTEGRAÇÃO DO NÚCLEO CONVERSACIONAL

Valida a cadeia:

    Interface 56.5.1
            ↓
    Transporte 56.5.2
            ↓
    Integração Sessão ↔ Transporte 56.5.4
            ↓
    Núcleo Conversacional
            ↓
    Agente / domínio

O teste utiliza subclasses determinísticas de Agente e Compositor,
sem consultar Qwen, para que o resultado seja reprodutível.

Objetivos:

1. validar construção das camadas;
2. validar processamento ponta a ponta;
3. validar criação automática de sessão;
4. validar reutilização da sessão;
5. validar propagação do ID até o núcleo;
6. validar fallback por domínio;
7. validar resposta estruturada;
8. validar contrato da interface;
9. validar fechamento da sessão;
10. validar rejeição após fechamento;
11. validar isolamento estrutural;
12. garantir que nenhum conhecimento permanente ou alteração
    arquitetural seja produzido pela cadeia.
"""

from __future__ import annotations

import os
import sys
import time
import types
from copy import deepcopy
from unittest.mock import patch

# A cadeia é validada sem modelo: o runner do CI não tem ollama instalado.
ollama_fake = types.ModuleType("ollama")
ollama_fake.chat = lambda **_kwargs: {"message": {"content": "resposta simulada"}}
ollama_fake.Client = type("Client", (), {})
sys.modules.setdefault("ollama", ollama_fake)

from nixal_interface import (
    InterfaceConversacionalNixal,
)
from nixal_transporte_conversacional import (
    TransporteConversacionalNixal,
)
from nixal_integracao_sessao_transporte import (
    IntegracaoSessaoTransporteNixal,
)
from nixal_nucleo_conversacional import (
    NucleoConversacionalNixal,
)
from nixal_agente_qwen import (
    AgenteNixalQwen,
)
from nixal_composicao_56_3_9 import (
    CompositorNixal,
)
from nixal_dialogo_qwen import (
    DialogoQwenNixal,
)
from nixal_memoria_conversacional import (
    MemoriaConversacionalNixal,
)
from nixal_capacidades import (
    GerenciadorCapacidades,
)


TESTES = 0
FALHAS = 0


def verificar(
    condicao: bool,
    mensagem: str,
) -> None:

    global TESTES, FALHAS

    TESTES += 1

    if condicao:
        return

    FALHAS += 1

    print(
        f"FALHA: {mensagem}"
    )


class AgenteDeterministico(
    AgenteNixalQwen
):

    def __init__(self) -> None:
        super().__init__()

        self.chamadas = []

    def atender(
        self,
        necessidade: str,
    ) -> dict:

        self.chamadas.append(
            necessidade
        )

        if necessidade == "Que horas são?":

            return {
                "atendida": True,
                "necessidade": necessidade,
                "capacidade_escolhida": "obter_hora",
                "argumentos": {},
                "selecao": {
                    "sucesso": True,
                    "capacidade": "obter_hora",
                    "argumentos": {},
                    "candidatos": [],
                    "tentativa_correcao": False,
                    "erro": None,
                    "motivo": "validada",
                    "score_semantico": 1.0,
                },
                "resultado": {
                    "sucesso": True,
                    "capacidade": "obter_hora",
                    "resultado": {
                        "hora": 23,
                        "minuto": 30,
                        "segundo": 15,
                        "timestamp": 0.0,
                    },
                    "erro": None,
                    "timestamp": 0.0,
                    "duracao_ms": 0.1,
                },
            }

        if (
            necessidade
            == "Descobrir o horário atual do sistema."
        ):

            return {
                "atendida": True,
                "necessidade": necessidade,
                "capacidade_escolhida": "obter_hora",
                "argumentos": {},
                "selecao": {
                    "sucesso": True,
                    "capacidade": "obter_hora",
                    "argumentos": {},
                    "candidatos": [],
                    "tentativa_correcao": False,
                    "erro": None,
                    "motivo": "validada",
                    "score_semantico": 1.0,
                },
                "resultado": {
                    "sucesso": True,
                    "capacidade": "obter_hora",
                    "resultado": {
                        "hora": 23,
                        "minuto": 30,
                        "segundo": 16,
                        "timestamp": 0.0,
                    },
                    "erro": None,
                    "timestamp": 0.0,
                    "duracao_ms": 0.1,
                },
            }

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
                "motivo": (
                    "Nenhuma capacidade possui "
                    "evidência suficiente."
                ),
            },
            "resultado": None,
        }


class CompositorDeterministico(
    CompositorNixal
):

    def obter_contexto_dominio(
        self,
        necessidade: str,
    ) -> dict:

        if necessidade == (
            "Obter a hora atual do sistema."
        ):

            return {
                "dominio_origem": (
                    "sistema_computacional"
                ),
                "origem": {
                    "dominios": ["sistema_computacional"],
                    "melhor_score": 3,
                    "pontuacoes": {
                        "sistema_computacional": 3,
                    },
                },
                "classificacao_semantica": None,
                "capacidades_prioritarias": [
                    "obter_hora"
                ],
            }

        return {
            "dominio_origem": "externo",
            "origem": {
                "dominios": [],
                "melhor_score": 0,
                "pontuacoes": {},
            },
            "classificacao_semantica": None,
            "capacidades_prioritarias": [],
        }


class DialogoDeterministico(
    DialogoQwenNixal
):

    """Sem modelo: a cadeia não pode depender de um LLM para ser validada."""

    def __init__(self) -> None:
        self.provedor = "deterministico"
        self.modelo = "deterministico"
        self.cliente = None
        self.gerenciador_capacidades = None
        self._ferramentas_operacionais_registradas = False
        self.chamadas = []

    def responder(
        self,
        texto: str,
        **argumentos,
    ) -> dict:

        self.chamadas.append(texto)

        return {
            "sucesso": False,
            "origem": "dialogo_deterministico",
            "resposta": None,
            "erro": "modelo não é usado nesta cadeia",
        }



def construir_ambiente():
    interface = (
        InterfaceConversacionalNixal()
    )

    transporte = (
        TransporteConversacionalNixal(
            interface
        )
    )

    integracao = (
        IntegracaoSessaoTransporteNixal(
            transporte
        )
    )

    agente = (
        AgenteDeterministico()
    )

    compositor = (
        CompositorDeterministico()
    )

    dialogo = (
        DialogoDeterministico()
    )

    # O teste não pode escrever no histórico real do usuário instalado.
    with patch.dict(
        os.environ,
        {MemoriaConversacionalNixal.VARIAVEL_CAMINHO: ""},
    ):
        memoria = (
            MemoriaConversacionalNixal()
        )

    nucleo = (
        NucleoConversacionalNixal(
            interface=interface,
            agente=agente,
            compositor=compositor,
            dialogo=dialogo,
            memoria_conversacional=memoria,
        )
    )

    return (
        interface,
        transporte,
        integracao,
        agente,
        compositor,
        nucleo,
    )


def teste_construcao() -> None:

    (
        interface,
        transporte,
        integracao,
        agente,
        compositor,
        nucleo,
    ) = construir_ambiente()

    verificar(
        isinstance(
            interface,
            InterfaceConversacionalNixal,
        ),
        "interface deve ser criada corretamente",
    )

    verificar(
        isinstance(
            transporte,
            TransporteConversacionalNixal,
        ),
        "transporte deve ser criado corretamente",
    )

    verificar(
        isinstance(
            integracao,
            IntegracaoSessaoTransporteNixal,
        ),
        "integração deve ser criada corretamente",
    )

    verificar(
        isinstance(
            agente,
            AgenteNixalQwen,
        ),
        "agente determinístico deve manter contrato do 55.3",
    )

    verificar(
        isinstance(
            compositor,
            CompositorNixal,
        ),
        "compositor determinístico deve manter contrato da composição",
    )

    verificar(
        isinstance(
            nucleo,
            NucleoConversacionalNixal,
        ),
        "núcleo deve ser criado corretamente",
    )

    verificar(
        nucleo.interface is interface,
        "núcleo deve usar a interface injetada",
    )

    verificar(
        nucleo.agente is agente,
        "núcleo deve usar o agente injetado",
    )

    verificar(
        nucleo.compositor is compositor,
        "núcleo deve usar o compositor injetado",
    )


def teste_primeira_mensagem() -> None:

    (
        interface,
        transporte,
        integracao,
        agente,
        compositor,
        nucleo,
    ) = construir_ambiente()

    resultado = (
        integracao.processar_mensagem(
            "Que horas são?",
            nucleo,
        )
    )

    verificar(
        resultado["sucesso"] is True,
        "primeira mensagem deve ter sucesso",
    )

    verificar(
        resultado["estado"]
        == "mensagem_processada_com_sessao",
        "estado integrado deve ser mensagem_processada_com_sessao",
    )

    verificar(
        isinstance(
            resultado["sessao"],
            str,
        )
        and bool(resultado["sessao"]),
        "primeira mensagem deve criar ID de sessão",
    )

    verificar(
        resultado["valor"]["sessao"]["estado"]
        == "ativa",
        "sessão criada deve estar ativa",
    )

    verificar(
        resultado["valor"]["sessao_criada_agora"]
        is True,
        "primeira mensagem deve marcar criação da sessão",
    )

    verificar(
        resultado["valor"]["mensagem_armazenada"]
        is True,
        "mensagem deve ser armazenada na memória conversacional recente",
    )

    verificar(
        resultado["valor"]["memoria_conversacional"]
        is True,
        "memória conversacional recente deve alimentar a cadeia",
    )

    verificar(
        resultado["valor"]["conhecimento_permanente"]
        is False,
        "conhecimento permanente deve permanecer falso",
    )

    verificar(
        resultado["valor"]["arquitetura_modificada"]
        is False,
        "arquitetura não deve ser modificada",
    )

    transporte_resultado = (
        resultado["valor"]["transporte"]
    )

    verificar(
        transporte_resultado["sucesso"]
        is True,
        "transporte deve ter sucesso",
    )

    resposta = (
        transporte_resultado["resposta"]
    )

    verificar(
        resposta["resposta"]
        == "Agora são 23:30:15.",
        "resposta da primeira mensagem deve ser correta",
    )

    verificar(
        resposta["sessao"]
        == resultado["sessao"],
        "ID da sessão deve chegar à resposta",
    )

    verificar(
        interface.validar_resposta(
            resposta
        ),
        "resposta deve respeitar 56.5.1",
    )

    verificar(
        agente.chamadas
        == ["Que horas são?"],
        "primeira mensagem deve chegar ao agente",
    )


def teste_segunda_mensagem_mesma_sessao() -> None:

    (
        interface,
        transporte,
        integracao,
        agente,
        compositor,
        nucleo,
    ) = construir_ambiente()

    primeira = (
        integracao.processar_mensagem(
            "Que horas são?",
            nucleo,
        )
    )

    sessao = primeira["sessao"]

    segunda = (
        integracao.processar_mensagem(
            "Obter a hora atual do sistema.",
            nucleo,
            sessao_id=sessao,
        )
    )

    verificar(
        segunda["sucesso"] is True,
        "segunda mensagem deve ter sucesso",
    )

    verificar(
        segunda["sessao"]
        == sessao,
        "segunda mensagem deve manter a mesma sessão",
    )

    verificar(
        segunda["valor"]["sessao_criada_agora"]
        is False,
        "segunda mensagem não deve criar nova sessão",
    )

    verificar(
        segunda["valor"]["sessao"]["id"]
        == sessao,
        "sessão retornada deve ser a original",
    )

    verificar(
        segunda["valor"]["sessao"]["estado"]
        == "ativa",
        "sessão deve continuar ativa",
    )

    resposta = (
        segunda["valor"]["transporte"]["resposta"]
    )

    verificar(
        resposta["resposta"]
        == "Agora são 23:30:16.",
        "segunda resposta deve ser correta",
    )

    verificar(
        resposta["sessao"]
        == sessao,
        "resposta deve preservar a sessão",
    )

    verificar(
        interface.validar_resposta(
            resposta
        ),
        "segunda resposta deve respeitar 56.5.1",
    )

    verificar(
        agente.chamadas
        == [
            "Que horas são?",
            "Obter a hora atual do sistema.",
            "Descobrir o horário atual do sistema.",
        ],
        "fallback por domínio deve usar objetivo canônico",
    )

    verificar(
        resposta["valor"]["modo"]
        == "resposta_capacidade",
        "capacidade deve responder sem cair no modelo",
    )

    verificar(
        nucleo.dialogo.chamadas
        == [],
        "cadeia determinística não pode consultar um modelo",
    )

    verificar(
        resposta["valor"]["memoria_conversacional_estado"]["permanente"]
        is False,
        "memória recente não pode se apresentar como conhecimento permanente",
    )


def teste_fechamento_e_rejeicao() -> None:

    (
        interface,
        transporte,
        integracao,
        agente,
        compositor,
        nucleo,
    ) = construir_ambiente()

    primeira = (
        integracao.processar_mensagem(
            "Que horas são?",
            nucleo,
        )
    )

    sessao = primeira["sessao"]

    encerramento = (
        integracao.encerrar_sessao(
            sessao
        )
    )

    verificar(
        encerramento["sucesso"] is True,
        "sessão deve poder ser encerrada",
    )

    verificar(
        encerramento["estado"]
        == "sessao_encerrada",
        "estado deve ser sessao_encerrada",
    )

    estado = (
        integracao.obter_sessao(
            sessao
        )
    )

    verificar(
        estado["sucesso"] is True,
        "sessão encerrada deve continuar conhecida",
    )

    verificar(
        estado["valor"]["estado"]
        == "encerrada",
        "sessão deve ficar marcada como encerrada",
    )

    verificar(
        integracao.sessao_ativa(
            sessao
        ) is False,
        "sessão encerrada não deve estar ativa",
    )

    depois = (
        integracao.processar_mensagem(
            "Que horas são?",
            nucleo,
            sessao_id=sessao,
        )
    )

    verificar(
        depois["sucesso"] is False,
        "mensagem após encerramento deve ser rejeitada",
    )

    verificar(
        depois["estado"]
        == "sessao_inativa",
        "estado após encerramento deve ser sessao_inativa",
    )

    verificar(
        depois["sessao"]
        == sessao,
        "ID da sessão encerrada deve ser preservado",
    )

    verificar(
        len(agente.chamadas)
        == 1,
        "núcleo não deve receber mensagem de sessão inativa",
    )


def teste_isolamento_entrada() -> None:

    (
        interface,
        transporte,
        integracao,
        agente,
        compositor,
        nucleo,
    ) = construir_ambiente()

    entrada = interface.criar_entrada(
        "Que horas são?"
    )

    original = deepcopy(
        entrada
    )

    resposta = transporte.enviar_entrada(
        entrada,
        nucleo,
    )

    verificar(
        resposta["sucesso"] is True,
        "entrada estruturada deve passar pelo transporte",
    )

    verificar(
        entrada == original,
        "entrada original não deve ser modificada",
    )

    verificar(
        entrada["valor"]["processado"]
        is False,
        "entrada original deve permanecer não processada",
    )

    verificar(
        entrada["valor"]["capacidade_executada"]
        is False,
        "entrada original não deve declarar execução",
    )


def teste_entrada_invalida() -> None:

    (
        interface,
        transporte,
        integracao,
        agente,
        compositor,
        nucleo,
    ) = construir_ambiente()

    resultado = (
        integracao.enviar_entrada(
            None,
            nucleo,
        )
    )

    verificar(
        resultado["sucesso"] is False,
        "entrada None deve ser rejeitada",
    )


def teste_relogio_real_da_producao() -> None:
    """O agente do teste é fixo; a capacidade real continua lendo o sistema."""

    antes = time.localtime()
    resultado = GerenciadorCapacidades().executar("obter_hora")
    depois = time.localtime()

    verificar(
        resultado.sucesso is True,
        "capacidade obter_hora deve executar",
    )

    dados = resultado.resultado

    verificar(
        isinstance(dados, dict)
        and all(chave in dados for chave in ("hora", "minuto", "segundo")),
        "obter_hora deve devolver hora, minuto e segundo",
    )

    if isinstance(dados, dict):
        executar_horas = (dados["hora"], dados["minuto"], dados["segundo"])
        verificar(
            executar_horas
            in {
                (antes.tm_hour, antes.tm_min, antes.tm_sec),
                (depois.tm_hour, depois.tm_min, depois.tm_sec),
            },
            "obter_hora deve acompanhar o relógio do sistema, nunca um valor congelado",
        )


def executar_testes() -> None:

    teste_construcao()
    teste_primeira_mensagem()
    teste_segunda_mensagem_mesma_sessao()
    teste_relogio_real_da_producao()
    teste_fechamento_e_rejeicao()
    teste_isolamento_entrada()
    teste_entrada_invalida()

    print()
    print("=" * 60)
    print("TESTE — INTEGRAÇÃO NÚCLEO CONVERSACIONAL")
    print("=" * 60)
    print()
    print(
        f"TESTES EXECUTADOS: {TESTES}"
    )
    print(
        f"FALHAS: {FALHAS}"
    )
    print(
        f"PASSOU: {FALHAS == 0}"
    )
    print(
        "=" * 60
    )


if __name__ == "__main__":
    executar_testes()
