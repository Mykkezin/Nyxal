#!/usr/bin/env python3

from __future__ import annotations

from typing import Any


ESTADOS_CONSOLIDAVEIS = {
    "suportada",
}

TIPOS_CONHECIMENTO_PERMITIDOS = {
    "definicao",
    "funcao",
    "origem",
    "teste",
    "resultado",
    "limite",
    "evolucao",
    "estrutura",
    "incerteza",
}


def verificar(condicao: bool, mensagem: str) -> None:
    estado = "PASS" if condicao else "FALHA"
    print(f"[{estado}] {mensagem}")
    if not condicao:
        raise AssertionError(mensagem)


def consolidar_candidato(
    ciclo: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(ciclo, dict):
        return {
            "sucesso": False,
            "estado": "entrada_invalida",
            "motivo": "Ciclo inválido.",
        }

    estado = ciclo.get("estado_atual")

    if estado not in ESTADOS_CONSOLIDAVEIS:
        return {
            "sucesso": True,
            "estado": "nao_consolidavel",
            "motivo": (
                "Somente hipóteses no estado suportada "
                "podem gerar candidato nesta primeira versão."
            ),
            "conhecimento_permanente": False,
        }

    hipotese = ciclo.get("hipotese")

    if not isinstance(hipotese, str) or not hipotese.strip():
        return {
            "sucesso": False,
            "estado": "entrada_invalida",
            "motivo": "O ciclo não possui hipótese textual válida.",
        }

    avaliacoes = ciclo.get("avaliacoes")

    if not isinstance(avaliacoes, list) or not avaliacoes:
        return {
            "sucesso": False,
            "estado": "entrada_invalida",
            "motivo": "O ciclo não possui avaliação registrada.",
        }

    ultima_avaliacao = avaliacoes[-1]

    if not isinstance(ultima_avaliacao, dict):
        return {
            "sucesso": False,
            "estado": "entrada_invalida",
            "motivo": "A última avaliação não é válida.",
        }

    resultado_avaliacao = ultima_avaliacao.get("resultado")

    if not isinstance(resultado_avaliacao, dict):
        return {
            "sucesso": False,
            "estado": "entrada_invalida",
            "motivo": "A avaliação não possui resultado estruturado.",
        }

    if resultado_avaliacao.get("estado") != "suportada":
        return {
            "sucesso": True,
            "estado": "nao_consolidavel",
            "motivo": "A última avaliação não é suportada.",
            "conhecimento_permanente": False,
        }

    candidato = {
        "texto": hipotese,
        "tipo": "estrutura",
        "origem": {
            "estado": "suportada",
            "indice_avaliacao": ultima_avaliacao.get("indice"),
        },
        "conhecimento_permanente": False,
        "gravado": False,
    }

    return {
        "sucesso": True,
        "estado": "candidato_conhecimento_criado",
        "valor": candidato,
        "conhecimento_permanente": False,
        "arquitetura_modificada": False,
    }


def main() -> None:
    ciclo_suportado = {
        "hipotese": (
            "É possível que existam dependências entre os componentes "
            "da arquitetura que ainda não estão registradas formalmente "
            "na planta."
        ),
        "estado_atual": "suportada",
        "avaliacoes": [
            {
                "indice": 1,
                "estado_anterior": "testada",
                "resultado": {
                    "estado": "suportada",
                },
            }
        ],
        "conhecimento_permanente": False,
    }

    resultado = consolidar_candidato(
        ciclo_suportado
    )

    verificar(
        resultado.get("sucesso") is True,
        "gate aceita ciclo suportado",
    )

    verificar(
        resultado.get("estado")
        == "candidato_conhecimento_criado",
        "gate cria candidato de conhecimento",
    )

    candidato = resultado.get("valor", {})

    verificar(
        isinstance(candidato, dict),
        "candidato possui estrutura válida",
    )

    verificar(
        candidato.get("texto")
        == ciclo_suportado["hipotese"],
        "candidato preserva exatamente a hipótese",
    )

    verificar(
        candidato.get("tipo") in TIPOS_CONHECIMENTO_PERMITIDOS,
        "candidato usa tipo de conhecimento permitido",
    )

    verificar(
        candidato.get("gravado") is False,
        "candidato ainda não grava conhecimento",
    )

    verificar(
        candidato.get("conhecimento_permanente") is False,
        "candidato ainda não é conhecimento permanente",
    )

    verificar(
        resultado.get("conhecimento_permanente") is False,
        "resultado do gate continua não permanente",
    )

    verificar(
        resultado.get("arquitetura_modificada") is False,
        "gate não modifica arquitetura",
    )

    ciclo_nao_suportado = {
        "hipotese": "Hipótese qualquer.",
        "estado_atual": "refutada",
        "avaliacoes": [
            {
                "indice": 1,
                "resultado": {
                    "estado": "refutada",
                },
            }
        ],
    }

    recusado = consolidar_candidato(
        ciclo_nao_suportado
    )

    verificar(
        recusado.get("estado")
        == "nao_consolidavel",
        "estado refutada não gera candidato",
    )

    print("=" * 60)
    print("TESTE — GATE DE CONSOLIDAÇÃO DE CONHECIMENTO")
    print("=" * 60)
    print("PASSOU: True")
    print("=" * 60)


if __name__ == "__main__":
    main()
