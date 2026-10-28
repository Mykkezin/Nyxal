#!/usr/bin/env python3

"""
NIXAL — TESTE DA INTEGRAÇÃO SESSÃO ↔ TRANSPORTE

Microetapa 56.5.4

Valida:
1. criação automática de sessão na primeira mensagem;
2. reutilização da sessão ativa sem recriação;
3. encaminhamento de provedor e contexto de sistema isolados por cópia;
4. separação arquitetural (nada de memória nem conhecimento nesta camada);
5. consulta e estado ativo;
6. sessão inexistente;
7. encerramento e recusa após encerramento;
8. entrada estruturada e suas validações;
9. texto vazio e núcleo ausente;
10. falha ao criar uma nova sessão (sessao_nao_criada / sessao_invalida);
11. retry da requisição na mesma sessão e retry após queda do transporte;
12. reinício do processo servidor sobre o ID efêmero da sessão;
13. ausência de expiração (TTL) como característica da camada.

O histórico conversacional persistente não pertence a esta camada; a
recuperação depois de reinício real de processo é coberta por
teste_nixal_memoria_conversacional.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
        *,
        provedor: str | None = None,
        contexto_sistema: dict | None = None,
    ) -> dict:
        self.chamadas.append(
            {
                "texto": texto,
                "nucleo": nucleo,
                "sessao": sessao,
                "provedor": provedor,
                "contexto_sistema": contexto_sistema,
            }
        )

        return {
            "sucesso": True,
            "estado": "mensagem_processada",
            "origem": "transporte_teste",
            "sessao": sessao,
            "resposta": nucleo.processar(texto),
        }


class GerenciadorCriacaoFalha(GerenciadorSessoesNixal):
    """Simula o esgotamento do armazenamento de sessões em RAM."""

    def criar(self, sessao_id=None) -> dict:
        return {
            "sucesso": False,
            "estado": "operacao_negada",
            "sessao": None,
            "erro": "armazenamento indisponível",
        }


class GerenciadorIdInvalido(GerenciadorSessoesNixal):
    """Simula um gerenciador que confirma a criação sem devolver ID."""

    def criar(self, sessao_id=None) -> dict:
        return {
            "sucesso": True,
            "estado": "sessao_criada",
            "sessao": None,
        }


class TransporteInstavel:
    def __init__(self) -> None:
        self.chamadas = []

    def processar_mensagem(self, texto, nucleo, sessao) -> dict:
        self.chamadas.append({"texto": texto, "sessao": sessao})

        if len(self.chamadas) == 1:
            raise RuntimeError("queda transitória do transporte")

        return {
            "sucesso": True,
            "estado": "mensagem_processada",
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
    # 3 — OPÇÕES DE PROVEDOR SEM SEGUNDA CAMADA DE SESSÃO
    # --------------------------------------------------------

    contexto_sistema_teste = {"observabilidade": {"cpu_percent": 15.0}}
    resultado_opcoes = integracao.processar_mensagem(
        texto="Resuma o estado do sistema.",
        nucleo=nucleo,
        sessao_id=sessao_id,
        provedor="openai",
        contexto_sistema=contexto_sistema_teste,
    )
    verificar(
        resultado_opcoes.get("sucesso") is True,
        "opções de provedor não quebram o contrato de sessão",
    )
    verificar(
        transporte.chamadas[-1]["provedor"] == "openai",
        "integração encaminha o provedor selecionado",
    )
    verificar(
        transporte.chamadas[-1]["contexto_sistema"] == contexto_sistema_teste,
        "integração encaminha o contexto de leitura",
    )
    contexto_sistema_teste["observabilidade"]["cpu_percent"] = 99.0
    verificar(
        transporte.chamadas[-1]["contexto_sistema"]["observabilidade"]["cpu_percent"] == 15.0,
        "contexto é isolado por cópia profunda antes do transporte",
    )

    # --------------------------------------------------------
    # 4 — SEPARAÇÃO ARQUITETURAL
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
    # 10 — FALHA AO CRIAR UMA NOVA SESSÃO
    # --------------------------------------------------------

    transporte_falha = TransporteTeste()
    integracao_falha = IntegracaoSessaoTransporteNixal(
        transporte=transporte_falha,
        sessoes=GerenciadorCriacaoFalha(),
    )

    resultado_sem_sessao = integracao_falha.processar_mensagem(
        texto="Não há sessão disponível.",
        nucleo=nucleo,
    )

    verificar(
        resultado_sem_sessao.get("sucesso") is False,
        "falha ao criar sessão é reportada como erro",
    )

    verificar(
        resultado_sem_sessao.get("estado") == "sessao_nao_criada",
        "estado sessao_nao_criada está correto",
    )

    verificar(
        resultado_sem_sessao.get("sessao") is None,
        "nenhum ID de sessão é inventado na falha de criação",
    )

    verificar(
        len(transporte_falha.chamadas) == 0,
        "recusa por falha de criação não chega ao transporte",
    )

    transporte_id_invalido = TransporteTeste()
    integracao_id_invalido = IntegracaoSessaoTransporteNixal(
        transporte=transporte_id_invalido,
        sessoes=GerenciadorIdInvalido(),
    )

    resultado_id_invalido = integracao_id_invalido.processar_mensagem(
        texto="Sessão sem identificador.",
        nucleo=nucleo,
    )

    verificar(
        resultado_id_invalido.get("estado") == "sessao_invalida",
        "sessão criada sem ID válido é rejeitada",
    )

    verificar(
        len(transporte_id_invalido.chamadas) == 0,
        "sessão sem ID não é entregue ao transporte",
    )

    # --------------------------------------------------------
    # 11 — RETRY DA MESMA REQUISIÇÃO
    # --------------------------------------------------------

    transporte_retry = TransporteTeste()
    sessoes_retry = GerenciadorSessoesNixal()
    integracao_retry = IntegracaoSessaoTransporteNixal(
        transporte=transporte_retry,
        sessoes=sessoes_retry,
    )

    primeira = integracao_retry.processar_mensagem(
        texto="Repete a mesma coisa.",
        nucleo=nucleo,
    )
    sessao_retry = primeira.get("sessao")

    # Retry do cliente com o mesmo texto: a camada não deduplica,
    # então o transporte vê as duas tentativas e o cliente recebe a
    # mesma sessão nas duas.
    segunda = integracao_retry.processar_mensagem(
        texto="Repete a mesma coisa.",
        nucleo=nucleo,
        sessao_id=sessao_retry,
    )

    verificar(
        segunda.get("sucesso") is True,
        "retry da requisição é aceito pela sessão ativa",
    )

    verificar(
        segunda.get("sessao") == sessao_retry,
        "retry reutiliza a mesma sessão",
    )

    verificar(
        segunda.get("valor", {}).get("sessao_criada_agora") is False,
        "retry não cria uma segunda sessão",
    )

    verificar(
        sessoes_retry.listar().get("quantidade") == 1,
        "retry não duplica sessões no gerenciador",
    )

    verificar(
        primeira.get("valor", {}).get("sessao")
        == segunda.get("valor", {}).get("sessao"),
        "retry preserva o estado estrutural da sessão",
    )

    verificar(
        len(transporte_retry.chamadas) == 2,
        "retry é entregue ao transporte sem deduplicação nesta camada",
    )

    # Retry após falha do transporte: a recusa não pode consumir a sessão.
    transporte_instavel = TransporteInstavel()
    nucleo_instavel = NucleoTeste()
    integracao_instavel = IntegracaoSessaoTransporteNixal(
        transporte=transporte_instavel,
    )

    queda = integracao_instavel.processar_mensagem(
        texto="Mensagem que o transporte perdeu.",
        nucleo=nucleo_instavel,
    )

    verificar(
        queda.get("sucesso") is False,
        "exceção do transporte é reportada como falha",
    )

    verificar(
        queda.get("estado") == "transporte_nao_respondeu",
        "estado transporte_nao_respondeu está correto",
    )

    sessao_pos_queda = queda.get("sessao")

    verificar(
        integracao_instavel.sessao_ativa(sessao_pos_queda) is True,
        "sessão permanece ativa depois da queda do transporte",
    )

    reapresentacao = integracao_instavel.processar_mensagem(
        texto="Mensagem que o transporte perdeu.",
        nucleo=nucleo_instavel,
        sessao_id=sessao_pos_queda,
    )

    verificar(
        reapresentacao.get("sucesso") is True,
        "retry da mesma mensagem após a queda prospera",
    )

    verificar(
        reapresentacao.get("sessao") == sessao_pos_queda,
        "retry após a queda usa a sessão original",
    )

    verificar(
        len(transporte_instavel.chamadas) == 2,
        "as duas tentativas ficam registradas no transporte",
    )

    # --------------------------------------------------------
    # 12 — REINÍCIO DO PROCESSO SERVIDOR
    # --------------------------------------------------------

    sessoes_antes = GerenciadorSessoesNixal()
    transporte_reinicio = TransporteTeste()
    integracao_antes = IntegracaoSessaoTransporteNixal(
        transporte=transporte_reinicio,
        sessoes=sessoes_antes,
    )

    antes_do_reinicio = integracao_antes.processar_mensagem(
        texto="Conversa antes do reinício.",
        nucleo=nucleo,
    )
    sessao_antes = antes_do_reinicio.get("sessao")
    chamadas_antes = len(transporte_reinicio.chamadas)

    # O processo morre e renasce: as sessões vivem em RAM, então o
    # gerenciador novo começa sem nenhuma identidade conhecida.
    integracao_depois = IntegracaoSessaoTransporteNixal(
        transporte=transporte_reinicio,
        sessoes=GerenciadorSessoesNixal(),
    )

    verificar(
        integracao_depois.sessao_ativa(sessao_antes) is False,
        "sessão anterior ao reinício não está ativa no processo novo",
    )

    replay = integracao_depois.processar_mensagem(
        texto="Conversa antes do reinício.",
        nucleo=nucleo,
        sessao_id=sessao_antes,
    )

    verificar(
        replay.get("sucesso") is False,
        "replay com ID de antes do reinício é rejeitado",
    )

    verificar(
        replay.get("estado") == "sessao_nao_valida",
        "replay após reinício recebe sessao_nao_valida",
    )

    verificar(
        replay.get("valor", {}).get("detalhes", {}).get("estado")
        == "sessao_desconhecida",
        "rejeição distingue sessão desconhecida de sessão encerrada",
    )

    verificar(
        len(transporte_reinicio.chamadas) == chamadas_antes,
        "replay recusado após reinício não chega ao transporte",
    )

    depois_do_reinicio = integracao_depois.processar_mensagem(
        texto="Retomando depois do reinício.",
        nucleo=nucleo,
    )

    verificar(
        depois_do_reinicio.get("sucesso") is True,
        "mensagem sem ID cria sessão nova após o reinício",
    )

    verificar(
        depois_do_reinicio.get("sessao") != sessao_antes,
        "o ID anterior não é reutilizado: não é credencial durável",
    )

    verificar(
        integracao_depois.obter_sessao(sessao_antes).get("estado")
        == "sessao_desconhecida",
        "a consulta pós-reinício responde sessão desconhecida",
    )

    verificar(
        integracao_depois.obter_sessao(sessao_antes).get("valor") is None,
        "nenhum conteúdo é recuperado da sessão antiga",
    )

    # --------------------------------------------------------
    # 13 — LIMITE DA CAMADA SOBRE O HISTÓRICO
    # --------------------------------------------------------

    # "Expirada" não existe como estado: o gerenciador só tem ativa e
    # encerrada, sem TTL. A continuidade do histórico pertence à memória
    # conversacional, não a esta camada.
    estrutura_sessao = depois_do_reinicio.get("valor", {}).get("sessao", {})

    verificar(
        set(estrutura_sessao) == {"id", "estado", "criada_em", "encerrada_em"},
        "sessão carrega apenas identidade e estado estrutural",
    )

    verificar(
        estrutura_sessao.get("estado") == "ativa",
        "sessão nova após reinício está ativa",
    )

    verificar(
        estrutura_sessao.get("encerrada_em") is None,
        "sessão ativa não possui encerramento registrado",
    )

    verificar(
        "Conversa antes do reinício." not in str(estrutura_sessao),
        "nenhum texto de conversa é transportado pela sessão",
    )

    verificar(
        depois_do_reinicio.get("valor", {}).get("mensagem_armazenada") is False,
        "a camada não armazena a mensagem retomada",
    )

    verificar(
        depois_do_reinicio.get("valor", {}).get("memoria_conversacional") is False,
        "a camada não acessa a memória conversacional",
    )

    # --------------------------------------------------------
    # 14 — AUSÊNCIA DE EXPIRAÇÃO (TTL)
    # --------------------------------------------------------

    # "Expirada" não é um estado desta camada: o gerenciador só conhece
    # ativa e encerrada. O relógio injetável deixa provar isso em vez de
    # apenas afirmar — é a evidência de que a sessão é efêmera por
    # omissão, não por política de expiração.
    relogio = {"agora": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    sessoes_sem_ttl = GerenciadorSessoesNixal(relogio=lambda: relogio["agora"])
    transporte_sem_ttl = TransporteTeste()
    integracao_sem_ttl = IntegracaoSessaoTransporteNixal(
        transporte=transporte_sem_ttl,
        sessoes=sessoes_sem_ttl,
    )

    antiga = integracao_sem_ttl.processar_mensagem(
        texto="Sessão criada em 2026.",
        nucleo=nucleo,
    )
    criada_em = antiga.get("valor", {}).get("sessao", {}).get("criada_em")

    verificar(
        criada_em == "2026-01-01T00:00:00+00:00",
        "a sessão registra o instante do relógio injetado",
    )

    relogio["agora"] += timedelta(days=3650)

    depois_dez_anos = integracao_sem_ttl.processar_mensagem(
        texto="Ainda vale?",
        nucleo=nucleo,
        sessao_id=antiga.get("sessao"),
    )

    verificar(
        depois_dez_anos.get("sucesso") is True,
        "sessão de dez anos atrás continua aceitando mensagens",
    )

    verificar(
        depois_dez_anos.get("valor", {}).get("sessao", {}).get("estado")
        == "ativa",
        "o tempo avançado não altera o estado da sessão",
    )

    verificar(
        depois_dez_anos.get("valor", {}).get("sessao", {}).get("criada_em")
        == criada_em,
        "a criação não é reescrita pelo relógio",
    )

    verificar(
        len(transporte_sem_ttl.chamadas) == 2,
        "o transporte recebeu as duas mensagens da mesma sessão",
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
