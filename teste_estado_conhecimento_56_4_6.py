#!/usr/bin/env python3

"""
NIXAL — TESTE DO ESTADO DE CONHECIMENTO

Microetapa 56.4.6

Valida a distinção entre:

    conhecido
    nao_declarado
    desconhecido

A camada não deve transformar ausência de declaração em
afirmação de inexistência.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_autorreprentacao import AutorreprentacaoNixal
from nixal_consulta_interna import ConsultaInternaNixal
from nixal_estado_conhecimento import (
    ESTADO_CONHECIDO,
    ESTADO_DESCONHECIDO,
    ESTADO_NAO_DECLARADO,
    EstadoConhecimentoNixal,
)


ARQUIVO_PLANTA = (
    Path(__file__).resolve().parent
    / "planta_nixal"
    / "planta.json"
)


def hash_planta() -> str:
    return hashlib.sha256(
        ARQUIVO_PLANTA.read_bytes()
    ).hexdigest()


def assert_passou(
    nome: str,
    condicao: bool,
) -> bool:
    print(
        f"[{'PASS' if condicao else 'FAIL'}] {nome}"
    )
    return condicao


def main() -> None:
    autor = AutorreprentacaoNixal()
    consulta = ConsultaInternaNixal(
        autorrepresentacao=autor
    )
    estado = EstadoConhecimentoNixal(
        consulta_interna=consulta
    )

    resultados: list[bool] = []

    hash_antes = hash_planta()

    capacidade_conhecida = estado.capacidade(
        "ler_estado_corpo"
    )

    resultados.append(
        assert_passou(
            "1. capacidade declarada é conhecida",
            capacidade_conhecida.get("estado")
            == ESTADO_CONHECIDO
            and capacidade_conhecida.get("valor")
            is True,
        )
    )

    capacidade_ausente = estado.capacidade(
        "camera"
    )

    resultados.append(
        assert_passou(
            "2. capacidade ausente é não declarada",
            capacidade_ausente.get("estado")
            == ESTADO_NAO_DECLARADO
            and capacidade_ausente.get("valor")
            is None,
        )
    )

    resultados.append(
        assert_passou(
            "3. não declarado não significa inexistente",
            capacidade_ausente.get("estado")
            == ESTADO_NAO_DECLARADO
            and capacidade_ausente.get("valor")
            is None,
        )
    )

    componente_conhecido = estado.componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "4. componente declarado é conhecido",
            componente_conhecido.get("estado")
            == ESTADO_CONHECIDO
            and componente_conhecido.get("valor", {}).get(
                "id"
            )
            == "corpo_computacional",
        )
    )

    componente_ausente = estado.componente(
        "camera"
    )

    resultados.append(
        assert_passou(
            "5. componente ausente é não declarado",
            componente_ausente.get("estado")
            == ESTADO_NAO_DECLARADO
            and componente_ausente.get("valor")
            is None,
        )
    )

    funcao_conhecida = estado.funcao_componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "6. função de componente declarada é conhecida",
            funcao_conhecida.get("estado")
            == ESTADO_CONHECIDO
            and isinstance(
                funcao_conhecida.get("valor"),
                str,
            ),
        )
    )

    funcao_ausente = estado.funcao_componente(
        "camera"
    )

    resultados.append(
        assert_passou(
            "7. função de componente ausente é não declarada",
            funcao_ausente.get("estado")
            == ESTADO_NAO_DECLARADO,
        )
    )

    resposta_conhecida = estado.classificar_resposta(
        {
            "sucesso": True,
            "estado": ESTADO_CONHECIDO,
            "valor": "teste",
        }
    )

    resultados.append(
        assert_passou(
            "8. resposta conhecida preserva conhecido",
            resposta_conhecida.get("estado")
            == ESTADO_CONHECIDO
            and resposta_conhecida.get("valor")
            == "teste",
        )
    )

    resposta_desconhecida = estado.classificar_resposta(
        {
            "sucesso": True,
            "estado": ESTADO_DESCONHECIDO,
            "valor": None,
        }
    )

    resultados.append(
        assert_passou(
            "9. desconhecido permanece desconhecido",
            resposta_desconhecida.get("estado")
            == ESTADO_DESCONHECIDO,
        )
    )

    resposta_negada = estado.classificar_resposta(
        {
            "sucesso": False,
            "estado": "negado",
            "valor": None,
        }
    )

    resultados.append(
        assert_passou(
            "10. consulta negada não vira conhecimento",
            resposta_negada.get("estado")
            == ESTADO_DESCONHECIDO,
        )
    )

    resultados.append(
        assert_passou(
            "11. camada usa consulta interna",
            estado.consulta is consulta,
        )
    )

    resultados.append(
        assert_passou(
            "12. camada não acessa a planta diretamente",
            not hasattr(
                estado,
                "caminho_planta",
            )
        )
    )

    resultados.append(
        assert_passou(
            "13. camada não executa capacidades",
            not hasattr(
                estado,
                "executar_capacidade",
            )
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "14. classificação não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    print()
    print("=" * 60)
    print(
        f"TESTES EXECUTADOS: {len(resultados)}"
    )
    print(
        f"FALHAS: {sum(not resultado for resultado in resultados)}"
    )
    print(
        f"PASSOU: {all(resultados)}"
    )
    print("=" * 60)

    if not all(resultados):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
