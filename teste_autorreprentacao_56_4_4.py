#!/usr/bin/env python3

"""
NIXAL — TESTE DA AUTORREPRESENTAÇÃO INTEGRADA

Microetapa 56.4.4

Valida a integração da autorrepresentação com a planta real
através do LeitorPlantaNixal.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_autorreprentacao import (
    AutorreprentacaoNixal,
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

    resultados: list[bool] = []

    hash_antes = hash_planta()

    identidade = autor.identidade()

    resultados.append(
        assert_passou(
            "1. autorrepresentação lê identidade real",
            identidade.get("estado") == "conhecido"
            and identidade.get("origem")
            == "planta_nixal"
            and identidade.get("valor", {}).get("nome")
            == "Nixal",
        )
    )

    componentes = autor.componentes()

    resultados.append(
        assert_passou(
            "2. autorrepresentação lê componentes reais",
            componentes.get("estado") == "conhecido"
            and len(componentes.get("valor", [])) == 11,
        )
    )

    corpo = autor.componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "3. componente real é encontrado",
            corpo.get("estado") == "conhecido"
            and corpo.get("valor", {}).get("id")
            == "corpo_computacional",
        )
    )

    funcao = autor.funcao_componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "4. função do componente é conhecida",
            funcao.get("estado") == "conhecido"
            and isinstance(
                funcao.get("valor"),
                str,
            ),
        )
    )

    capacidades = autor.capacidades()

    resultados.append(
        assert_passou(
            "5. capacidades reais são expostas",
            capacidades.get("estado") == "conhecido"
            and len(capacidades.get("valor", []))
            == 5,
        )
    )

    resultados.append(
        assert_passou(
            "6. capacidade ausente não é inventada",
            autor.possui_capacidade(
                "visao_computacional"
            ).get("estado")
            == "desconhecido",
        )
    )

    limites = autor.limites()

    resultados.append(
        assert_passou(
            "7. limites reais são expostos",
            limites.get("estado") == "conhecido"
            and len(limites.get("valor", []))
            >= 1,
        )
    )

    regras = autor.regras_modificacao()

    resultados.append(
        assert_passou(
            "8. regras de modificação são expostas",
            regras.get("estado") == "conhecido"
            and regras.get("valor", {}).get("planta")
            == "somente_leitura",
        )
    )

    pode_modificar_planta = autor.pode_modificar(
        "planta"
    )

    resultados.append(
        assert_passou(
            "9. planta continua protegida",
            pode_modificar_planta.get("estado")
            == "conhecido"
            and pode_modificar_planta.get("valor", {}).get(
                "pode_modificar"
            )
            is False,
        )
    )

    desconhecido = autor.componente(
        "camera"
    )

    resultados.append(
        assert_passou(
            "10. componente inexistente continua desconhecido",
            desconhecido.get("estado")
            == "desconhecido"
            and desconhecido.get("valor")
            is None,
        )
    )

    consulta = autor.consultar(
        "Quais capacidades você possui?"
    )

    resultados.append(
        assert_passou(
            "11. consulta usa a planta como origem",
            consulta.get("origem")
            == "planta_nixal"
            and consulta.get("estado")
            == "conhecido",
        )
    )

    snapshot = autor.snapshot()

    resultados.append(
        assert_passou(
            "12. snapshot possui origem formal",
            snapshot.get("origem")
            == "planta_nixal"
            and snapshot.get("estado")
            == "conhecido",
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "13. consulta não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    resultados.append(
        assert_passou(
            "14. autorrepresentação não inicia conversação",
            autor.consultar(
                "Olá, converse comigo."
            ).get("estado")
            == "desconhecido",
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
