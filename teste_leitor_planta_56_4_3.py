#!/usr/bin/env python3

"""
NIXAL — TESTE DO LEITOR DA PLANTA

Microetapa 56.4.3

Valida o leitor sobre a planta_nixal/planta.json real.
"""

from __future__ import annotations

import json
from pathlib import Path

from leitor_planta_nixal import (
    LeitorPlantaNixal,
)


ARQUIVO_PLANTA = (
    Path(__file__).resolve().parent
    / "planta_nixal"
    / "planta.json"
)


def assert_passou(
    nome: str,
    condicao: bool,
) -> bool:
    print(
        f"[{'PASS' if condicao else 'FAIL'}] {nome}"
    )
    return condicao


def main() -> None:
    leitor = LeitorPlantaNixal(
        ARQUIVO_PLANTA
    )

    resultados: list[bool] = []

    identidade = leitor.identidade()

    resultados.append(
        assert_passou(
            "1. leitura da identidade",
            identidade.get("nome") == "Nixal",
        )
    )

    resultados.append(
        assert_passou(
            "2. versão da arquitetura",
            identidade.get("versao_arquitetura")
            == "56.4.2",
        )
    )

    componentes = leitor.componentes()

    resultados.append(
        assert_passou(
            "3. leitura dos componentes",
            len(componentes) == 11,
        )
    )

    corpo = leitor.obter_componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "4. localizar componente conhecido",
            isinstance(corpo, dict)
            and corpo.get("estado") == "ativo",
        )
    )

    resultados.append(
        assert_passou(
            "5. função de componente conhecida",
            leitor.consultar(
                "Qual a função do componente corpo_computacional?"
            ).get("estado")
            == "conhecido",
        )
    )

    resultados.append(
        assert_passou(
            "6. capacidades conhecidas",
            len(leitor.capacidades()) == 5,
        )
    )

    resultados.append(
        assert_passou(
            "7. limites conhecidos",
            len(leitor.limites()) >= 1,
        )
    )

    resultados.append(
        assert_passou(
            "8. planta somente leitura",
            leitor.regra_modificacao("planta")
            == "somente_leitura",
        )
    )

    desconhecido_componente = leitor.consultar(
        "Qual a função do componente camera?"
    )

    resultados.append(
        assert_passou(
            "9. componente ausente vira desconhecido",
            desconhecido_componente.get(
                "estado"
            )
            == "desconhecido"
            and desconhecido_componente.get(
                "valor"
            )
            is None,
        )
    )

    desconhecido_sensor = leitor.consultar(
        "Você possui uma câmera?"
    )

    resultados.append(
        assert_passou(
            "10. sensor ausente não é inventado",
            desconhecido_sensor.get(
                "estado"
            )
            == "desconhecido"
            and desconhecido_sensor.get(
                "valor"
            )
            is None,
        )
    )

    consulta_inexistente = leitor.consultar(
        "Qual é a capacidade de controlar um braço robótico?"
    )

    resultados.append(
        assert_passou(
            "11. consulta não declarada não é inventada",
            consulta_inexistente.get(
                "estado"
            )
            == "desconhecido"
            and consulta_inexistente.get(
                "valor"
            )
            is None,
        )
    )

    copia = leitor.planta_completa()

    resultados.append(
        assert_passou(
            "12. acesso retorna cópia da planta",
            copia == leitor.planta_completa()
            and copia is not leitor._planta,
        )
    )

    resultados.append(
        assert_passou(
            "13. origem da resposta é a planta",
            leitor.consultar(
                "Quais componentes existem?"
            ).get("origem")
            == "planta_nixal",
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
