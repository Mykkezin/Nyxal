#!/usr/bin/env python3

"""
NIXAL — TESTE DE OPERAÇÃO SOBRE CONTEXTO

Microetapa 56.3.10 — protótipo 2

Objetivo:

Separar conceitualmente:

1. AÇÃO:
   uma necessidade que exige uma capacidade.

2. CONTEXTO:
   uma operação sobre informação que já foi obtida.

Este teste não usa Qwen e não executa capacidades reais.

Ele verifica se Nixal consegue:

- receber um contexto produzido por uma etapa anterior;
- localizar uma informação explicitamente pedida;
- devolver essa informação sem chamar nenhuma capacidade;
- diferenciar informação ausente de seleção ambígua;
- recusar quando a seleção é ambígua.

A ideia é preparar a arquitetura para que:

    capacidade -> produz informação
    contexto  -> organiza/seleciona informação
    capacidade -> consome nova informação

e não:

    contexto -> inventa uma nova capacidade.
"""

from __future__ import annotations

import json
import re
from typing import Any


# ================================================================
# NORMALIZAÇÃO
# ================================================================

def normalizar_texto(
    texto: str,
) -> str:

    texto = texto.lower()

    substituicoes = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    for origem, destino in (
        substituicoes.items()
    ):

        texto = texto.replace(
            origem,
            destino,
        )

    return texto


# ================================================================
# EXTRAÇÃO GENÉRICA DE NOMES DE ARQUIVOS
# ================================================================

def extrair_arquivos(
    valor: Any,
) -> list[str]:

    encontrados: list[str] = []

    def visitar(
        item: Any,
    ) -> None:

        if isinstance(
            item,
            dict,
        ):

            for valor_interno in item.values():

                visitar(
                    valor_interno
                )

            return

        if isinstance(
            item,
            list,
        ):

            for valor_interno in item:

                visitar(
                    valor_interno
                )

            return

        if isinstance(
            item,
            str,
        ):

            candidato = item.strip()

            if re.fullmatch(
                r"[^/\n]+",
                candidato,
            ) and "." in candidato:

                if candidato not in encontrados:

                    encontrados.append(
                        candidato
                    )

    visitar(
        valor
    )

    return encontrados


# ================================================================
# SELEÇÃO DE INFORMAÇÃO DO CONTEXTO
# ================================================================

def selecionar_arquivo_do_contexto(
    necessidade: str,
    contexto: dict[int, dict[str, Any]],
) -> dict[str, Any]:

    arquivos = []

    for arquivo in extrair_arquivos(
        contexto
    ):

        if arquivo.lower().endswith(
            ".json"
        ):

            if arquivo not in arquivos:

                arquivos.append(
                    arquivo
                )

    if not arquivos:

        return {
            "sucesso": False,
            "tipo": "contexto",
            "operacao": "selecionar",
            "valor": None,
            "erro": (
                "Nenhum arquivo JSON foi "
                "encontrado no contexto."
            ),
        }

    necessidade_normalizada = (
        normalizar_texto(
            necessidade
        )
    )

    # ------------------------------------------------------------
    # Procurar primeiro por um nome explícito.
    # ------------------------------------------------------------

    nomes_mencionados = re.findall(
        r"[\w.-]+\.json",
        necessidade_normalizada,
        re.IGNORECASE,
    )

    nomes_encontrados = []

    for nome in nomes_mencionados:

        for arquivo in arquivos:

            if (
                nome.lower()
                == arquivo.lower()
            ):

                if arquivo not in nomes_encontrados:

                    nomes_encontrados.append(
                        arquivo
                    )

    # ------------------------------------------------------------
    # Um nome explícito foi pedido.
    #
    # Se existir no contexto, selecionar.
    # Se não existir, declarar ausência.
    # ------------------------------------------------------------

    if len(
        nomes_mencionados
    ) == 1:

        if len(
            nomes_encontrados
        ) == 1:

            return {
                "sucesso": True,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": nomes_encontrados[0],
                "origem": "contexto",
                "candidatos": arquivos,
                "erro": None,
            }

        return {
            "sucesso": False,
            "tipo": "contexto",
            "operacao": "selecionar",
            "valor": None,
            "origem": "contexto",
            "candidatos": arquivos,
            "erro": (
                "A informação solicitada "
                "não existe no contexto."
            ),
        }

    # ------------------------------------------------------------
    # Mais de um nome explícito foi mencionado.
    # Se houver exatamente um correspondente, é seguro.
    # Caso contrário, não escolher arbitrariamente.
    # ------------------------------------------------------------

    if len(
        nomes_mencionados
    ) > 1:

        if len(
            nomes_encontrados
        ) == 1:

            return {
                "sucesso": True,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": nomes_encontrados[0],
                "origem": "contexto",
                "candidatos": arquivos,
                "erro": None,
            }

        return {
            "sucesso": False,
            "tipo": "contexto",
            "operacao": "selecionar",
            "valor": None,
            "candidatos": arquivos,
            "erro": (
                "A seleção explícita não pode "
                "ser resolvida com segurança."
            ),
        }

    # ------------------------------------------------------------
    # Sem nome explícito:
    # se houver apenas um candidato, a seleção
    # pode ser determinada pelo contexto.
    # ------------------------------------------------------------

    if len(
        arquivos
    ) == 1:

        return {
            "sucesso": True,
            "tipo": "contexto",
            "operacao": "selecionar",
            "valor": arquivos[0],
            "origem": "contexto",
            "candidatos": arquivos,
            "erro": None,
        }

    # ------------------------------------------------------------
    # Vários candidatos e nenhuma instrução suficiente:
    # não escolher arbitrariamente.
    # ------------------------------------------------------------

    return {
        "sucesso": False,
        "tipo": "contexto",
        "operacao": "selecionar",
        "valor": None,
        "candidatos": arquivos,
        "erro": (
            "A seleção é ambígua: existem vários "
            "arquivos possíveis no contexto."
        ),
    }


# ================================================================
# DEMONSTRAÇÃO
# ================================================================

def executar_teste(
    titulo: str,
    necessidade: str,
    contexto: dict[int, dict[str, Any]],
) -> dict[str, Any]:

    print()
    print("=" * 60)
    print(titulo)
    print("=" * 60)

    print()
    print("NECESSIDADE:")
    print(
        necessidade
    )

    print()
    print("CONTEXTO:")
    print(
        json.dumps(
            contexto,
            ensure_ascii=False,
            indent=2,
        )
    )

    resultado = (
        selecionar_arquivo_do_contexto(
            necessidade,
            contexto,
        )
    )

    print()
    print("RESULTADO:")
    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
        )
    )

    return resultado


# ================================================================
# MAIN
# ================================================================

def main() -> None:

    print()
    print("=" * 60)
    print(
        "NIXAL — TESTE DE OPERAÇÃO SOBRE CONTEXTO"
    )
    print(
        "MICROETAPA 56.3.10 — PROTÓTIPO 2"
    )
    print("=" * 60)

    contexto_1 = {
        1: {
            "necessidade": (
                "Listar os arquivos do projeto"
            ),
            "atendida": True,
            "sucesso_operacao": True,
            "resultado": {
                "sucesso": True,
                "capacidade": "listar_arquivos",
                "resultado": [
                    "nixal.py",
                    "capacidades_nixal.json",
                    "estado_corpo_nixal.json",
                    "memoria_corporal_nixal.json",
                ],
            },
        }
    }

    # ------------------------------------------------------------
    # TESTE 1
    # Seleção explícita e segura.
    # ------------------------------------------------------------

    resultado_1 = executar_teste(
        "TESTE 1 — SELEÇÃO EXPLÍCITA",
        (
            "Selecionar o arquivo "
            "capacidades_nixal.json da lista."
        ),
        contexto_1,
    )

    teste_1 = (
        resultado_1["sucesso"] is True
        and resultado_1["tipo"]
        == "contexto"
        and resultado_1["operacao"]
        == "selecionar"
        and resultado_1["valor"]
        == "capacidades_nixal.json"
        and resultado_1["origem"]
        == "contexto"
    )

    print()
    print(
        f"TESTE 1: {'PASSOU' if teste_1 else 'FALHOU'}"
    )

    # ------------------------------------------------------------
    # TESTE 2
    # Arquivo explicitamente pedido, mas ausente.
    # ------------------------------------------------------------

    resultado_2 = executar_teste(
        "TESTE 2 — INFORMAÇÃO AUSENTE",
        (
            "Selecionar o arquivo "
            "configuracao.json da lista."
        ),
        contexto_1,
    )

    teste_2 = (
        resultado_2["sucesso"] is False
        and resultado_2["valor"] is None
        and (
            "não existe"
            in resultado_2["erro"].lower()
        )
    )

    print()
    print(
        f"TESTE 2: {'PASSOU' if teste_2 else 'FALHOU'}"
    )

    # ------------------------------------------------------------
    # TESTE 3
    # Vários arquivos e nenhuma escolha explícita.
    # Não escolher arbitrariamente.
    # ------------------------------------------------------------

    resultado_3 = executar_teste(
        "TESTE 3 — SELEÇÃO AMBÍGUA",
        (
            "Selecione um arquivo JSON da lista."
        ),
        contexto_1,
    )

    teste_3 = (
        resultado_3["sucesso"] is False
        and resultado_3["valor"] is None
        and (
            "ambígua"
            in resultado_3["erro"].lower()
        )
    )

    print()
    print(
        f"TESTE 3: {'PASSOU' if teste_3 else 'FALHOU'}"
    )

    # ------------------------------------------------------------
    # RESULTADO FINAL
    # ------------------------------------------------------------

    passou = (
        teste_1
        and teste_2
        and teste_3
    )

    print()
    print("=" * 60)
    print(
        "RESULTADO FINAL: "
        f"{'PASSOU' if passou else 'FALHOU'}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
