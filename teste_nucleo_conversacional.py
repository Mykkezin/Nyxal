#!/usr/bin/env python3

"""
NIXAL — TESTE DO NÚCLEO CONVERSACIONAL

Teste estrutural do componente experimental:

    nixal_nucleo_conversacional.py

Objetivos:

1. validar importação e construção do núcleo;
2. validar entrada 56.5.1;
3. validar processamento direto pelo Agente 55.3;
4. validar fallback único por domínio;
5. validar ausência de fallback quando há ambiguidade;
6. validar ausência de capacidade para domínio externo;
7. validar formatação de resultado;
8. validar preservação de sessão;
9. validar ausência de modificação estrutural na resposta.

Os testes substituem as chamadas externas por comportamentos
determinísticos depois da construção do núcleo.
"""

from __future__ import annotations

from nixal_interface import InterfaceConversacionalNixal
from nixal_agente_qwen import AgenteNixalQwen
from nixal_composicao_56_3_9 import CompositorNixal
from nixal_nucleo_conversacional import (
    NucleoConversacionalNixal,
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


def resultado_sucesso(
    capacidade: str,
    dado,
) -> dict:

    return {
        "atendida": True,
        "necessidade": "teste",
        "capacidade_escolhida": capacidade,
        "argumentos": {},
        "selecao": {
            "sucesso": True,
            "capacidade": capacidade,
            "argumentos": {},
            "candidatos": [
                {
                    "nome": capacidade,
                    "descricao": "teste",
                    "objetivo": "teste",
                    "exemplos": [],
                    "argumentos": {},
                }
            ],
            "tentativa_correcao": False,
            "erro": None,
            "motivo": "validada",
            "score_semantico": 1.0,
        },
        "resultado": {
            "sucesso": True,
            "capacidade": capacidade,
            "resultado": dado,
            "erro": None,
            "timestamp": 0.0,
            "duracao_ms": 0.0,
        },
    }


def resultado_falha() -> dict:

    return {
        "atendida": False,
        "necessidade": "teste",
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


class AmbienteTeste:

    def __init__(self) -> None:

        self.interface = (
            InterfaceConversacionalNixal()
        )

        self.agente = (
            AgenteNixalQwen()
        )

        self.compositor = (
            CompositorNixal()
        )

        self.nucleo = (
            NucleoConversacionalNixal(
                interface=self.interface,
                agente=self.agente,
                compositor=self.compositor,
            )
        )

        self.chamadas_agente = []

        self.agente.atender = (
            self.atender
        )

        self.contexto_dominio = {
            "dominio_origem": "desconhecido",
            "capacidades_prioritarias": [],
        }

        self.compositor.obter_contexto_dominio = (
            self.obter_contexto_dominio
        )

    def atender(
        self,
        necessidade: str,
    ) -> dict:

        self.chamadas_agente.append(
            necessidade
        )

        if necessidade == (
            "Que horas são?"
        ):
            return resultado_sucesso(
                "obter_hora",
                {
                    "hora": 23,
                    "minuto": 30,
                    "segundo": 15,
                    "timestamp": 0.0,
                },
            )

        if necessidade == (
            "Descobrir o horário atual do sistema."
        ):
            return resultado_sucesso(
                "obter_hora",
                {
                    "hora": 23,
                    "minuto": 30,
                    "segundo": 16,
                    "timestamp": 0.0,
                },
            )

        return resultado_falha()

    def obter_contexto_dominio(
        self,
        necessidade: str,
    ) -> dict:

        return self.contexto_dominio


def teste_construcao() -> None:

    ambiente = AmbienteTeste()

    verificar(
        isinstance(
            ambiente.nucleo,
            NucleoConversacionalNixal,
        ),
        "núcleo deve ser instância correta",
    )

    verificar(
        ambiente.nucleo.interface
        is ambiente.interface,
        "núcleo deve preservar interface injetada",
    )

    verificar(
        ambiente.nucleo.agente
        is ambiente.agente,
        "núcleo deve preservar agente injetado",
    )

    verificar(
        ambiente.nucleo.compositor
        is ambiente.compositor,
        "núcleo deve preservar compositor injetado",
    )


def teste_entrada_direta() -> None:

    ambiente = AmbienteTeste()

    entrada = (
        ambiente.interface.criar_entrada(
            "Que horas são?"
        )
    )

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    verificar(
        resposta["sucesso"] is True,
        "entrada direta deve gerar sucesso",
    )

    verificar(
        resposta["estado"]
        == "resposta_pronta",
        "estado da resposta deve ser resposta_pronta",
    )

    verificar(
        resposta["resposta"]
        == "Agora são 23:30:15.",
        "hora deve ser formatada corretamente",
    )

    verificar(
        ambiente.interface.validar_resposta(
            resposta
        ),
        "resposta direta deve respeitar 56.5.1",
    )

    verificar(
        ambiente.chamadas_agente
        == ["Que horas são?"],
        "caso direto deve chamar agente uma vez",
    )


def teste_fallback_dominio() -> None:

    ambiente = AmbienteTeste()

    entrada = (
        ambiente.interface.criar_entrada(
            "Obter a hora atual do sistema.",
            sessao="sessao-teste",
        )
    )

    ambiente.contexto_dominio = {
        "dominio_origem": (
            "sistema_computacional"
        ),
        "capacidades_prioritarias": [
            "obter_hora"
        ],
    }

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    verificar(
        resposta["sucesso"] is True,
        "fallback por domínio deve funcionar",
    )

    verificar(
        resposta["sessao"]
        == "sessao-teste",
        "sessão deve ser preservada",
    )

    verificar(
        resposta["resposta"]
        == "Agora são 23:30:16.",
        "fallback deve produzir resposta formatada",
    )

    verificar(
        ambiente.chamadas_agente
        == [
            "Obter a hora atual do sistema.",
            "Descobrir o horário atual do sistema.",
        ],
        "fallback deve usar o objetivo canônico",
    )

    verificar(
        ambiente.interface.validar_resposta(
            resposta
        ),
        "resposta do fallback deve ser válida",
    )


def teste_fallback_dominio_fraco_nao_forca_capacidade() -> None:

    ambiente = AmbienteTeste()

    ambiente.contexto_dominio = {
        "dominio_origem": "sistema_computacional",
        "origem": {
            "melhor_score": 1,
            "dominios": ["sistema_computacional"],
            "evidencias": ["sistema"],
        },
        "capacidades_prioritarias": [
            "obter_hora"
        ],
    }

    entrada = (
        ambiente.interface.criar_entrada(
            "Qual é o sistema operacional que estou construindo?"
        )
    )

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    verificar(
        resposta["estado"]
        == "resposta_pronta",
        "evidência de domínio fraca não deve forçar uma capacidade",
    )

    verificar(
        ambiente.chamadas_agente
        == [
            "Qual é o sistema operacional que estou construindo?"
        ],
        "fallback não deve substituir a necessidade original por um objetivo arbitrário",
    )


def teste_ambiguidade() -> None:

    ambiente = AmbienteTeste()

    entrada = (
        ambiente.interface.criar_entrada(
            "Quero listar os arquivos do projeto."
        )
    )

    ambiente.contexto_dominio = {
        "dominio_origem": (
            "projeto_arquivo"
        ),
        "capacidades_prioritarias": [
            "listar_arquivos",
            "ler_arquivo",
        ],
    }

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    verificar(
        resposta["sucesso"] is True,
        "caso ambíguo deve produzir resposta estrutural",
    )

    verificar(
        resposta["resposta"]
        == (
            "Não consegui atender essa solicitação "
            "com as capacidades atuais."
        ),
        "caso ambíguo não deve escolher capacidade automaticamente",
    )

    verificar(
        ambiente.chamadas_agente
        == [
            "Quero listar os arquivos do projeto."
        ],
        "caso ambíguo não deve fazer segunda tentativa",
    )


def teste_externo() -> None:

    ambiente = AmbienteTeste()

    entrada = (
        ambiente.interface.criar_entrada(
            "Preciso descobrir a temperatura do mundo."
        )
    )

    ambiente.contexto_dominio = {
        "dominio_origem": "externo",
        "capacidades_prioritarias": [],
    }

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    verificar(
        resposta["sucesso"] is True,
        "caso externo deve manter contrato de resposta",
    )

    verificar(
        resposta["resposta"]
        == (
            "Não consegui atender essa solicitação "
            "com as capacidades atuais."
        ),
        "caso externo não deve inventar capacidade",
    )

    verificar(
        ambiente.chamadas_agente
        == [
            "Preciso descobrir a temperatura do mundo."
        ],
        "caso externo não deve gerar segunda tentativa",
    )


def teste_formatacao_lista() -> None:

    ambiente = AmbienteTeste()

    resposta = ambiente.interface.criar_resposta(
        ambiente.nucleo._formatar_dado(
            [
                "arquivo_a.py",
                "arquivo_b.py",
            ]
        )
    )

    verificar(
        resposta["resposta"]
        == (
            "Encontrei estes itens:\n"
            "- arquivo_a.py\n"
            "- arquivo_b.py"
        ),
        "lista deve ser formatada corretamente",
    )


def teste_formatacao_string() -> None:

    ambiente = AmbienteTeste()

    texto = (
        ambiente.nucleo._formatar_dado(
            "resultado textual"
        )
    )

    verificar(
        texto == "resultado textual",
        "string deve ser preservada",
    )


def teste_formatacao_vazia() -> None:

    ambiente = AmbienteTeste()

    texto = (
        ambiente.nucleo._formatar_dado([])
    )

    verificar(
        texto == "Não encontrei itens.",
        "lista vazia deve ter mensagem definida",
    )


def teste_flags_interface() -> None:

    ambiente = AmbienteTeste()

    entrada = (
        ambiente.interface.criar_entrada(
            "Que horas são?"
        )
    )

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    valor = resposta["valor"]

    verificar(
        valor["interpretado"] is False,
        "interface não deve marcar interpretação",
    )

    verificar(
        valor["capacidade_executada"] is False,
        "interface não deve marcar execução própria",
    )

    verificar(
        valor["conhecimento_permanente"] is False,
        "resposta não deve promover conhecimento permanente",
    )

    verificar(
        valor["arquitetura_modificada"] is False,
        "resposta não deve indicar alteração arquitetural",
    )


def teste_entrada_invalida() -> None:

    ambiente = AmbienteTeste()

    resposta = (
        ambiente.nucleo.processar(
            {}
        )
    )

    verificar(
        resposta["sucesso"] is True,
        "núcleo deve produzir resposta estruturada para entrada inválida",
    )

    verificar(
        resposta["estado"]
        == "entrada_invalida",
        "entrada inválida deve possuir estado específico",
    )

    verificar(
        ambiente.interface.validar_resposta(
            resposta
        ),
        "resposta de entrada inválida deve respeitar contrato",
    )


def teste_sessao_nula() -> None:

    ambiente = AmbienteTeste()

    entrada = (
        ambiente.interface.criar_entrada(
            "Que horas são?"
        )
    )

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    verificar(
        resposta["sessao"] is None,
        "sessão ausente deve continuar None no núcleo",
    )


def teste_capacidade_inexistente() -> None:

    ambiente = AmbienteTeste()

    entrada = (
        ambiente.interface.criar_entrada(
            "Teste"
        )
    )

    ambiente.contexto_dominio = {
        "dominio_origem": (
            "sistema_computacional"
        ),
        "capacidades_prioritarias": [
            "capacidade_inexistente"
        ],
    }

    resposta = (
        ambiente.nucleo.processar(
            entrada
        )
    )

    verificar(
        resposta["resposta"]
        == (
            "Não consegui atender essa solicitação "
            "com as capacidades atuais."
        ),
        "capacidade inexistente não deve ser executada",
    )

    verificar(
        ambiente.chamadas_agente
        == ["Teste"],
        "capacidade inexistente não deve gerar segunda chamada",
    )


def executar_testes() -> None:

    teste_construcao()
    teste_entrada_direta()
    teste_fallback_dominio()
    teste_fallback_dominio_fraco_nao_forca_capacidade()
    teste_ambiguidade()
    teste_externo()
    teste_formatacao_lista()
    teste_formatacao_string()
    teste_formatacao_vazia()
    teste_flags_interface()
    teste_entrada_invalida()
    teste_sessao_nula()
    teste_capacidade_inexistente()

    print()
    print("=" * 60)
    print("TESTE — NÚCLEO CONVERSACIONAL")
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
