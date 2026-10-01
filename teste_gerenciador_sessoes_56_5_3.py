#!/usr/bin/env python3

"""
NIXAL — TESTE DO GERENCIADOR DE SESSÕES

Microetapa 56.5.3

Valida:
1. criação automática de sessão;
2. criação com identificador explícito;
3. rejeição de identificador duplicado;
4. rejeição de identificador inválido;
5. consulta de sessão existente;
6. consulta de sessão desconhecida;
7. validação de sessão ativa;
8. encerramento de sessão;
9. validação após encerramento;
10. rejeição de encerramento duplicado;
11. listagem de sessões;
12. listagem somente de sessões ativas;
13. isolamento das estruturas retornadas;
14. ausência de memória conversacional;
15. ausência de mensagens;
16. ausência de conhecimento;
17. ausência de operações sobre arquitetura;
18. estado interno preservado diante de mutação externa.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

from nixal_gerenciador_sessoes import (
    GerenciadorSessoesNixal,
)


def main() -> None:
    falhas: list[str] = []
    total_testes = 0

    def verificar(
        condicao: bool,
        mensagem: str,
    ) -> None:
        nonlocal total_testes

        total_testes += 1

        if condicao:
            print(f"[PASS] {mensagem}")
        else:
            print(f"[FAIL] {mensagem}")
            falhas.append(mensagem)

    # ============================================================
    # RELÓGIO E IDs DETERMINÍSTICOS
    # ============================================================

    contador_id = 0

    def gerar_id() -> UUID:
        nonlocal contador_id

        contador_id += 1

        return UUID(
            f"00000000-0000-4000-8000-{contador_id:012d}"
        )

    instante = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    gerenciador = GerenciadorSessoesNixal(
        gerador_id=gerar_id,
        relogio=lambda: instante,
    )

    # ============================================================
    # CRIAÇÃO AUTOMÁTICA
    # ============================================================

    criada = gerenciador.criar()

    verificar(
        criada["sucesso"] is True,
        "criação automática de sessão é aceita",
    )

    verificar(
        criada["estado"] == "sessao_criada",
        "estado da criação é sessao_criada",
    )

    verificar(
        isinstance(criada.get("sessao"), str)
        and bool(criada["sessao"]),
        "sessão criada possui identificador",
    )

    verificar(
        criada["valor"]["id"]
        == criada["sessao"],
        "valor interno possui o mesmo identificador",
    )

    verificar(
        criada["valor"]["estado"] == "ativa",
        "nova sessão começa ativa",
    )

    verificar(
        criada["valor"]["criada_em"]
        == instante.isoformat(),
        "timestamp de criação é determinístico",
    )

    verificar(
        criada["valor"]["encerrada_em"] is None,
        "nova sessão não possui encerramento",
    )

    verificar(
        criada["versao_sessoes"] == "56.5.3",
        "versão da sessão é 56.5.3",
    )

    sessao_automatica = criada["sessao"]

    # ============================================================
    # ID AUTOMÁTICO VÁLIDO
    # ============================================================

    try:
        UUID(sessao_automatica)

        id_uuid_valido = True

    except (ValueError, AttributeError):
        id_uuid_valido = False

    verificar(
        id_uuid_valido,
        "identificador automático possui formato UUID válido",
    )

    # ============================================================
    # CRIAÇÃO EXPLÍCITA
    # ============================================================

    sessao_explicita_id = (
        "sessao-teste-explicita"
    )

    criada_explicita = gerenciador.criar(
        sessao_explicita_id
    )

    verificar(
        criada_explicita["sucesso"] is True,
        "criação de sessão com identificador explícito é aceita",
    )

    verificar(
        criada_explicita["sessao"]
        == sessao_explicita_id,
        "identificador explícito é preservado",
    )

    verificar(
        criada_explicita["valor"]["estado"]
        == "ativa",
        "sessão explícita começa ativa",
    )

    # ============================================================
    # DUPLICAÇÃO
    # ============================================================

    duplicada = gerenciador.criar(
        sessao_explicita_id
    )

    verificar(
        duplicada["sucesso"] is False,
        "identificador duplicado é rejeitado",
    )

    verificar(
        duplicada["estado"]
        == "operacao_negada",
        "duplicação retorna operação_negada",
    )

    # ============================================================
    # IDENTIFICADORES INVÁLIDOS
    # ============================================================

    invalida_vazia = gerenciador.criar("")

    verificar(
        invalida_vazia["sucesso"] is False,
        "identificador vazio é rejeitado",
    )

    invalida_espacos = gerenciador.criar("   ")

    verificar(
        invalida_espacos["sucesso"] is False,
        "identificador somente com espaços é rejeitado",
    )

    invalida_tipo = gerenciador.criar(None)

    verificar(
        invalida_tipo["sucesso"] is True,
        "quando o identificador é omitido, a geração automática é usada",
    )

    verificar(
        invalida_tipo["estado"]
        == "sessao_criada",
        "criação sem ID explícito continua válida",
    )

    sessao_terceira = invalida_tipo["sessao"]

    verificar(
        sessao_terceira not in {
            sessao_automatica,
            sessao_explicita_id,
        },
        "nova sessão automática recebe identificador distinto",
    )

    # ============================================================
    # CONSULTA
    # ============================================================

    consulta = gerenciador.obter(
        sessao_automatica
    )

    verificar(
        consulta["sucesso"] is True,
        "consulta de sessão existente é aceita",
    )

    verificar(
        consulta["estado"]
        == "sessao_encontrada",
        "consulta retorna sessao_encontrada",
    )

    verificar(
        consulta["sessao"]
        == sessao_automatica,
        "consulta preserva identificador",
    )

    verificar(
        consulta["valor"]["estado"]
        == "ativa",
        "sessão consultada permanece ativa",
    )

    # ============================================================
    # CONSULTA DESCONHECIDA
    # ============================================================

    desconhecida = gerenciador.obter(
        "sessao-inexistente"
    )

    verificar(
        desconhecida["sucesso"] is True,
        "consulta desconhecida não gera exceção",
    )

    verificar(
        desconhecida["estado"]
        == "sessao_desconhecida",
        "sessão inexistente permanece desconhecida",
    )

    verificar(
        desconhecida["valor"] is None,
        "sessão desconhecida não produz estrutura inventada",
    )

    # ============================================================
    # VALIDAÇÃO ATIVA
    # ============================================================

    validacao = gerenciador.validar(
        sessao_automatica
    )

    verificar(
        validacao["sucesso"] is True,
        "validação de sessão existente é aceita",
    )

    verificar(
        validacao["valida"] is True,
        "sessão existente é válida",
    )

    verificar(
        validacao["ativa"] is True,
        "sessão recém-criada está ativa",
    )

    verificar(
        gerenciador.esta_ativa(
            sessao_automatica
        ) is True,
        "esta_ativa reconhece sessão ativa",
    )

    # ============================================================
    # LISTAGEM
    # ============================================================

    todas = gerenciador.listar()

    verificar(
        todas["sucesso"] is True,
        "listagem geral é aceita",
    )

    verificar(
        todas["quantidade"] == 3,
        "há exatamente três sessões conhecidas",
    )

    verificar(
        len(todas["sessoes"]) == 3,
        "listagem retorna três estruturas de sessão",
    )

    ativas = gerenciador.listar(
        somente_ativas=True
    )

    verificar(
        ativas["sucesso"] is True,
        "listagem de sessões ativas é aceita",
    )

    verificar(
        ativas["somente_ativas"] is True,
        "filtro de sessões ativas é preservado",
    )

    verificar(
        ativas["quantidade"] == 3,
        "as três sessões estão ativas antes dos encerramentos",
    )

    # ============================================================
    # ISOLAMENTO DA CONSULTA
    # ============================================================

    consulta_isolada = gerenciador.obter(
        sessao_automatica
    )

    copia_consulta = deepcopy(
        consulta_isolada
    )

    copia_consulta["valor"]["estado"] = (
        "mutacao_externa"
    )

    verificar(
        consulta_isolada["valor"]["estado"]
        == "ativa",
        "mutação da cópia local não altera a resposta original",
    )

    consulta_nova = gerenciador.obter(
        sessao_automatica
    )

    verificar(
        consulta_nova["valor"]["estado"]
        == "ativa",
        "mutação externa não altera estado interno da sessão",
    )

    # ============================================================
    # ISOLAMENTO DA LISTAGEM
    # ============================================================

    listagem_isolada = gerenciador.listar()

    copia_listagem = deepcopy(
        listagem_isolada
    )

    copia_listagem["sessoes"][0]["estado"] = (
        "mutacao_externa"
    )

    listagem_nova = gerenciador.listar()

    verificar(
        all(
            sessao["estado"] != "mutacao_externa"
            for sessao in listagem_nova["sessoes"]
        ),
        "mutação externa da listagem não altera estado interno",
    )

    # ============================================================
    # AUSÊNCIA DE MEMÓRIA CONVERSACIONAL
    # ============================================================

    estrutura = gerenciador.obter(
        sessao_automatica
    )["valor"]

    verificar(
        "mensagens" not in estrutura,
        "sessão não armazena mensagens",
    )

    verificar(
        "historico" not in estrutura,
        "sessão não armazena histórico",
    )

    verificar(
        "memoria" not in estrutura,
        "sessão não armazena memória conversacional",
    )

    verificar(
        "conhecimento" not in estrutura,
        "sessão não armazena conhecimento",
    )

    verificar(
        "hipoteses" not in estrutura,
        "sessão não armazena hipóteses",
    )

    # ============================================================
    # SEPARAÇÃO ARQUITETURAL
    # ============================================================

    verificar(
        not hasattr(
            gerenciador,
            "processar_mensagem",
        ),
        "gerenciador não processa mensagens",
    )

    verificar(
        not hasattr(
            gerenciador,
            "executar_capacidade",
        ),
        "gerenciador não executa capacidades",
    )

    verificar(
        not hasattr(
            gerenciador,
            "formular_hipotese",
        ),
        "gerenciador não formula hipóteses",
    )

    verificar(
        not hasattr(
            gerenciador,
            "modificar_arquitetura",
        ),
        "gerenciador não modifica arquitetura",
    )

    # ============================================================
    # ENCERRAMENTO
    # ============================================================

    encerrada = gerenciador.encerrar(
        sessao_automatica
    )

    verificar(
        encerrada["sucesso"] is True,
        "encerramento de sessão é aceito",
    )

    verificar(
        encerrada["estado"]
        == "sessao_encerrada",
        "encerramento retorna sessao_encerrada",
    )

    verificar(
        encerrada["valor"]["estado"]
        == "encerrada",
        "estado da sessão muda para encerrada",
    )

    verificar(
        encerrada["valor"]["encerrada_em"]
        == instante.isoformat(),
        "timestamp de encerramento é determinístico",
    )

    verificar(
        gerenciador.esta_ativa(
            sessao_automatica
        ) is False,
        "sessão encerrada deixa de estar ativa",
    )

    # ============================================================
    # VALIDAÇÃO APÓS ENCERRAMENTO
    # ============================================================

    validacao_final = gerenciador.validar(
        sessao_automatica
    )

    verificar(
        validacao_final["valida"] is True,
        "sessão encerrada continua sendo uma sessão conhecida",
    )

    verificar(
        validacao_final["ativa"] is False,
        "sessão encerrada é marcada como inativa",
    )

    # ============================================================
    # ENCERRAMENTO DUPLICADO
    # ============================================================

    encerramento_duplicado = gerenciador.encerrar(
        sessao_automatica
    )

    verificar(
        encerramento_duplicado["sucesso"] is False,
        "encerramento duplicado é rejeitado",
    )

    verificar(
        encerramento_duplicado["estado"]
        == "sessao_ja_encerrada",
        "encerramento duplicado retorna estado específico",
    )

    # ============================================================
    # LISTAGEM APÓS ENCERRAMENTO
    # ============================================================

    ativas_apos = gerenciador.listar(
        somente_ativas=True
    )

    verificar(
        ativas_apos["quantidade"] == 2,
        "listagem somente ativas remove a sessão encerrada",
    )

    todas_apos = gerenciador.listar()

    verificar(
        todas_apos["quantidade"] == 3,
        "listagem geral preserva a sessão encerrada",
    )

    # ============================================================
    # SESSÃO DESCONHECIDA APÓS ENCERRAMENTO
    # ============================================================

    validar_desconhecida = gerenciador.validar(
        "outra-sessao-inexistente"
    )

    verificar(
        validar_desconhecida["valida"] is False,
        "sessão inexistente não é considerada válida",
    )

    verificar(
        validar_desconhecida["ativa"] is False,
        "sessão inexistente não é considerada ativa",
    )

    # ============================================================
    # RESULTADO FINAL
    # ============================================================

    print()
    print("=" * 60)
    print("TESTE — GERENCIADOR DE SESSÕES 56.5.3")
    print("=" * 60)
    print(f"TESTES EXECUTADOS: {total_testes}")
    print(f"FALHAS: {len(falhas)}")
    print(f"PASSOU: {not falhas}")
    print("=" * 60)

    if falhas:
        print()
        print("FALHAS ENCONTRADAS:")
        for falha in falhas:
            print(f"- {falha}")

        raise SystemExit(1)


if __name__ == "__main__":
    main()
