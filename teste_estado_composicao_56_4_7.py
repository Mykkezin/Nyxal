#!/usr/bin/env python3

"""
NIXAL — TESTE DO ESTADO COMPOSTO

Microetapa 56.4.7
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_autorreprentacao import AutorreprentacaoNixal
from nixal_consulta_interna import ConsultaInternaNixal
from nixal_estado_composicao import (
    EstadoCompostoAutorreprentacaoNixal,
)
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

    estado_conhecimento = EstadoConhecimentoNixal(
        consulta_interna=consulta
    )

    estado = EstadoCompostoAutorreprentacaoNixal(
        autorrepresentacao=autor,
        consulta_interna=consulta,
        estado_conhecimento=estado_conhecimento,
    )

    resultados: list[bool] = []
    hash_antes = hash_planta()

    snapshot = estado.construir()
    valor = snapshot.get("valor")

    resultados.append(
        assert_passou(
            "1. estado composto é conhecido",
            snapshot.get("sucesso") is True
            and snapshot.get("estado")
            == ESTADO_CONHECIDO,
        )
    )

    resultados.append(
        assert_passou(
            "2. snapshot contém identidade",
            isinstance(valor, dict)
            and valor.get("identidade", {}).get(
                "valor", {}
            ).get("nome")
            == "Nixal",
        )
    )

    resultados.append(
        assert_passou(
            "3. snapshot contém estado da arquitetura",
            isinstance(valor, dict)
            and valor.get(
                "estado_arquitetura", {}
            ).get("estado")
            == ESTADO_CONHECIDO,
        )
    )

    resultados.append(
        assert_passou(
            "4. snapshot contém os 11 componentes",
            isinstance(valor, dict)
            and len(
                valor.get(
                    "componentes", {}
                ).get(
                    "valor",
                    []
                )
            )
            == 11,
        )
    )

    resultados.append(
        assert_passou(
            "5. snapshot contém as 5 capacidades",
            isinstance(valor, dict)
            and len(
                valor.get(
                    "capacidades", {}
                ).get(
                    "valor",
                    []
                )
            )
            == 5,
        )
    )

    resultados.append(
        assert_passou(
            "6. snapshot contém limites",
            isinstance(valor, dict)
            and len(
                valor.get(
                    "limites", {}
                ).get(
                    "valor",
                    []
                )
            )
            >= 1,
        )
    )

    resultados.append(
        assert_passou(
            "7. snapshot contém regras de modificação",
            isinstance(valor, dict)
            and valor.get(
                "regras_modificacao", {}
            ).get(
                "valor", {}
            ).get("planta")
            == "somente_leitura",
        )
    )

    componente = estado.estado_componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "8. componente conhecido mantém estado conhecido",
            componente.get("estado")
            == ESTADO_CONHECIDO,
        )
    )

    componente_ausente = estado.estado_componente(
        "camera"
    )

    resultados.append(
        assert_passou(
            "9. componente ausente vira não declarado",
            componente_ausente.get("estado")
            == ESTADO_NAO_DECLARADO,
        )
    )

    capacidade = estado.estado_capacidade(
        "ler_estado_corpo"
    )

    resultados.append(
        assert_passou(
            "10. capacidade conhecida mantém estado conhecido",
            capacidade.get("estado")
            == ESTADO_CONHECIDO,
        )
    )

    capacidade_ausente = estado.estado_capacidade(
        "camera"
    )

    resultados.append(
        assert_passou(
            "11. capacidade ausente vira não declarada",
            capacidade_ausente.get("estado")
            == ESTADO_NAO_DECLARADO,
        )
    )

    funcao = estado.estado_funcao_componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "12. função conhecida é preservada",
            funcao.get("estado")
            == ESTADO_CONHECIDO
            and isinstance(
                funcao.get("valor"),
                str,
            ),
        )
    )

    campo_existente = estado.consultar_campo(
        "componentes"
    )

    resultados.append(
        assert_passou(
            "13. campo declarado pode ser consultado",
            campo_existente.get("estado")
            == ESTADO_CONHECIDO,
        )
    )

    campo_inexistente = estado.consultar_campo(
        "objetivos"
    )

    resultados.append(
        assert_passou(
            "14. campo não declarado permanece desconhecido",
            campo_inexistente.get("estado")
            == ESTADO_DESCONHECIDO
            and campo_inexistente.get("valor")
            is None,
        )
    )

    resumo = estado.resumo()

    resultados.append(
        assert_passou(
            "15. resumo identifica corretamente a arquitetura",
            resumo.get("valor", {}).get("nome")
            == "Nixal"
            and resumo.get(
                "valor", {}
            ).get(
                "versao_arquitetura"
            )
            == "56.4.2",
        )
    )

    executar = estado.executar_capacidade(
        "ler_estado_corpo"
    )

    resultados.append(
        assert_passou(
            "16. estado composto não executa capacidades",
            executar.get("estado")
            == "negado",
        )
    )

    modificar = estado.modificar("planta")

    resultados.append(
        assert_passou(
            "17. estado composto não se modifica",
            modificar.get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "18. estado composto usa a autorrepresentação",
            estado.autorrepresentacao is autor,
        )
    )

    resultados.append(
        assert_passou(
            "19. estado composto usa a consulta interna",
            estado.consulta_interna is consulta,
        )
    )

    resultados.append(
        assert_passou(
            "20. estado composto usa o estado de conhecimento",
            estado.estado_conhecimento is estado_conhecimento,
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "21. construção do estado não modifica a planta",
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
