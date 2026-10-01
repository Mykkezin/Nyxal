#!/usr/bin/env python3

from __future__ import annotations

from uuid import uuid4

from nixal_gerenciador_sessoes import GerenciadorSessoesNixal
from nixal_integracao_sessao_transporte import (
    IntegracaoSessaoTransporteNixal,
)


class NucleoTeste:
    def __init__(self) -> None:
        self.mensagens = []

    def processar(self, texto: str) -> str:
        self.mensagens.append(texto)
        return f"RESPOSTA: {texto}"


class TransporteTeste:
    def __init__(self) -> None:
        self.chamadas = []

    def processar_mensagem(
        self,
        texto: str,
        nucleo,
        sessao: str,
    ) -> dict:
        self.chamadas.append(
            {
                "texto": texto,
                "nucleo": nucleo,
                "sessao": sessao,
            }
        )

        return {
            "sucesso": True,
            "estado": "mensagem_processada",
            "origem": "transporte_teste",
            "sessao": sessao,
            "resposta": nucleo.processar(texto),
        }


def teste(condicao: bool, descricao: str, falhas: list[str]) -> None:
    if condicao:
        print(f"[PASS] {descricao}")
    else:
        print(f"[FAIL] {descricao}")
        falhas.append(descricao)


def main() -> None:
    falhas = []
    executados = 0

    def verificar(condicao: bool, descricao: str) -> None:
        nonlocal executados
        executados += 1
        teste(condicao, descricao, falhas)

    print("=" * 60)
    print("NIXAL — TESTE INTEGRAÇÃO SESSÃO ↔ TRANSPORTE 56.5.4")
    print("=" * 60)

    transporte = TransporteTeste()
    sessoes = GerenciadorSessoesNixal()

    integracao = IntegracaoSessaoTransporteNixal(
        transporte=transporte,
        sessoes=sessoes,
    )

    nucleo = NucleoTeste()

    verificar(
        integracao.VERSAO == "56.5.4",
        "versão da integração é 56.5.4",
    )

    # --------------------------------------------------------
    # 1 — CRIAÇÃO AUTOMÁTICA
    # --------------------------------------------------------

    resultado_1 = integracao.processar_mensagem(
        texto="Olá, Nixal.",
        nucleo=nucleo,
    )

    sessao_id = resultado_1.get("sessao")

    verificar(
        resultado_1.get("sucesso") is True,
        "mensagem sem sessão é processada",
    )

    verificar(
        resultado_1.get("estado")
        == "mensagem_processada_com_sessao",
        "estado integrado correto",
    )

    verificar(
        isinstance(sessao_id, str) and bool(sessao_id),
        "sessão criada possui ID válido",
    )

    verificar(
        resultado_1.get("valor", {})
        .get("sessao_criada_agora")
        is True,
        "primeira mensagem cria sessão",
    )

    verificar(
        transporte.chamadas[-1]["sessao"] == sessao_id,
        "transporte recebe o ID da sessão",
    )

    verificar(
        resultado_1.get("valor", {})
        .get("transporte", {})
        .get("sessao")
        == sessao_id,
        "resposta preserva o ID da sessão",
    )

    verificar(
        resultado_1.get("valor", {})
        .get("transporte", {})
        .get("resposta")
        == "RESPOSTA: Olá, Nixal.",
        "núcleo recebe a mensagem corretamente",
    )

    # --------------------------------------------------------
    # 2 — REUTILIZAÇÃO
    # --------------------------------------------------------

    resultado_2 = integracao.processar_mensagem(
        texto="Como está?",
        nucleo=nucleo,
        sessao_id=sessao_id,
    )

    verificar(
        resultado_2.get("sucesso") is True,
        "sessão ativa aceita nova mensagem",
    )

    verificar(
        resultado_2.get("sessao") == sessao_id,
        "segunda mensagem usa a mesma sessão",
    )

    verificar(
        resultado_2.get("valor", {})
        .get("sessao_criada_agora")
        is False,
        "sessão não é recriada",
    )

    verificar(
        transporte.chamadas[-1]["sessao"] == sessao_id,
        "transporte mantém o mesmo ID",
    )

    verificar(
        nucleo.mensagens == [
            "Olá, Nixal.",
            "Como está?",
        ],
        "núcleo recebeu as duas mensagens",
    )

    # --------------------------------------------------------
    # 3 — SEPARAÇÃO ARQUITETURAL
    # --------------------------------------------------------

    valor = resultado_2.get("valor", {})

    verificar(
        valor.get("mensagem_armazenada") is False,
        "mensagem não é armazenada",
    )

    verificar(
        valor.get("memoria_conversacional") is False,
        "memória conversacional permanece ausente",
    )

    verificar(
        valor.get("conhecimento_permanente") is False,
        "conhecimento permanente permanece False",
    )

    verificar(
        valor.get("arquitetura_modificada") is False,
        "arquitetura permanece inalterada",
    )

    # --------------------------------------------------------
    # 4 — CONSULTA
    # --------------------------------------------------------

    consulta = integracao.obter_sessao(sessao_id)

    verificar(
        consulta.get("sucesso") is True,
        "sessão pode ser consultada",
    )

    verificar(
        consulta.get("valor", {}).get("id") == sessao_id,
        "consulta retorna o mesmo ID",
    )

    verificar(
        consulta.get("valor", {}).get("estado") == "ativa",
        "sessão permanece ativa",
    )

    verificar(
        integracao.sessao_ativa(sessao_id) is True,
        "sessao_ativa retorna True",
    )

    # --------------------------------------------------------
    # 5 — SESSÃO INEXISTENTE
    # --------------------------------------------------------

    inexistente = str(uuid4())

    resultado_inexistente = integracao.processar_mensagem(
        texto="Teste.",
        nucleo=nucleo,
        sessao_id=inexistente,
    )

    verificar(
        resultado_inexistente.get("sucesso") is False,
        "sessão inexistente é rejeitada",
    )

    verificar(
        resultado_inexistente.get("estado")
        == "sessao_nao_valida",
        "estado de sessão inexistente está correto",
    )

    # --------------------------------------------------------
    # 6 — ENCERRAMENTO
    # --------------------------------------------------------

    encerramento = integracao.encerrar_sessao(sessao_id)

    verificar(
        encerramento.get("sucesso") is True,
        "sessão pode ser encerrada",
    )

    verificar(
        encerramento.get("valor", {}).get("estado")
        == "encerrada",
        "sessão fica encerrada",
    )

    verificar(
        integracao.sessao_ativa(sessao_id) is False,
        "sessão encerrada não está ativa",
    )

    # --------------------------------------------------------
    # 7 — APÓS ENCERRAMENTO
    # --------------------------------------------------------

    resultado_encerrada = integracao.processar_mensagem(
        texto="Ainda está aí?",
        nucleo=nucleo,
        sessao_id=sessao_id,
    )

    verificar(
        resultado_encerrada.get("sucesso") is False,
        "mensagem após encerramento é rejeitada",
    )

    verificar(
        resultado_encerrada.get("estado")
        == "sessao_inativa",
        "estado sessao_inativa está correto",
    )

    verificar(
        resultado_encerrada.get("sessao") == sessao_id,
        "ID da sessão encerrada é preservado",
    )

    # --------------------------------------------------------
    # 8 — ENTRADA ESTRUTURADA
    # --------------------------------------------------------

    entrada = {
        "sucesso": True,
        "estado": "entrada_recebida",
        "sessao": None,
        "valor": {
            "texto": "Entrada estruturada."
        },
    }

    # Nova integração para permitir criação automática.
    integracao_entrada = IntegracaoSessaoTransporteNixal(
        transporte=TransporteTeste(),
    )

    resultado_entrada = integracao_entrada.enviar_entrada(
        entrada=entrada,
        nucleo=nucleo,
    )

    verificar(
        resultado_entrada.get("sucesso") is True,
        "entrada estruturada é aceita",
    )

    verificar(
        isinstance(
            resultado_entrada.get("sessao"),
            str,
        ),
        "entrada estruturada recebe uma sessão",
    )

    # --------------------------------------------------------
    # 9 — VALIDAÇÕES DE ENTRADA
    # --------------------------------------------------------

    entrada_invalida = integracao.enviar_entrada(
        entrada=None,
        nucleo=nucleo,
    )

    verificar(
        entrada_invalida.get("sucesso") is False,
        "entrada None é rejeitada",
    )

    verificar(
        entrada_invalida.get("estado")
        == "operacao_negada",
        "entrada inválida possui estado correto",
    )

    texto_vazio = integracao.processar_mensagem(
        texto="   ",
        nucleo=nucleo,
    )

    verificar(
        texto_vazio.get("sucesso") is False,
        "texto vazio é rejeitado",
    )

    nucleo_ausente = integracao.processar_mensagem(
        texto="Teste sem núcleo.",
        nucleo=None,
    )

    verificar(
        nucleo_ausente.get("sucesso") is False,
        "núcleo ausente é rejeitado",
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("RESULTADO FINAL — 56.5.4")
    print("=" * 60)
    print(f"TESTES EXECUTADOS: {executados}")
    print(f"FALHAS: {len(falhas)}")
    print(f"PASSOU: {len(falhas) == 0}")

    if falhas:
        print()
        print("FALHAS:")
        for falha in falhas:
            print(f"- {falha}")

    print("=" * 60)

    if falhas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
