#!/usr/bin/env python3

"""
NIXAL — TESTE DA CONSULTA INTERNA

Microetapa 56.4.5

Valida que outra camada interna consegue consultar a
autorrepresentação sem acessar a planta diretamente,
sem inventar conhecimento e sem executar capacidades.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_autorreprentacao import (
    AutorreprentacaoNixal,
)
from nixal_consulta_interna import (
    ConsultaInternaNixal,
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

    resultados: list[bool] = []

    hash_antes = hash_planta()

    identidade = consulta.quem_sou()

    resultados.append(
        assert_passou(
            "1. consulta interna obtém a identidade",
            identidade.get("estado")
            == "conhecido"
            and identidade.get("origem")
            == "planta_nixal"
            and identidade.get("valor", {}).get("nome")
            == "Nixal",
        )
    )

    componentes = consulta.quais_componentes()

    resultados.append(
        assert_passou(
            "2. consulta interna obtém componentes",
            componentes.get("estado")
            == "conhecido"
            and len(componentes.get("valor", []))
            == 11,
        )
    )

    funcao = consulta.qual_funcao_do_componente(
        "corpo_computacional"
    )

    resultados.append(
        assert_passou(
            "3. consulta interna obtém função de componente",
            funcao.get("estado")
            == "conhecido"
            and isinstance(
                funcao.get("valor"),
                str,
            ),
        )
    )

    capacidades = consulta.quais_capacidades()

    resultados.append(
        assert_passou(
            "4. consulta interna obtém capacidades",
            capacidades.get("estado")
            == "conhecido"
            and len(capacidades.get("valor", []))
            == 5,
        )
    )

    capacidade_ausente = consulta.possuo_capacidade(
        "camera"
    )

    resultados.append(
        assert_passou(
            "5. capacidade ausente permanece desconhecida",
            capacidade_ausente.get("estado")
            == "desconhecido"
            and capacidade_ausente.get("valor")
            is None,
        )
    )

    limites = consulta.quais_sao_meus_limites()

    resultados.append(
        assert_passou(
            "6. consulta interna obtém limites",
            limites.get("estado")
            == "conhecido"
            and len(limites.get("valor", []))
            >= 1,
        )
    )

    regra_planta = consulta.como_posso_modificar(
        "planta"
    )

    resultados.append(
        assert_passou(
            "7. consulta interna preserva regra da planta",
            regra_planta.get("estado")
            == "conhecido"
            and regra_planta.get("valor", {}).get(
                "pode_modificar"
            )
            is False,
        )
    )

    desconhecido = consulta.qual_funcao_do_componente(
        "camera"
    )

    resultados.append(
        assert_passou(
            "8. componente inexistente não é inventado",
            desconhecido.get("estado")
            == "desconhecido"
            and desconhecido.get("valor")
            is None,
        )
    )

    operacao_invalida = consulta.consultar(
        "inventar_componente"
    )

    resultados.append(
        assert_passou(
            "9. operação não declarada é negada",
            operacao_invalida.get("sucesso")
            is False
            and operacao_invalida.get("estado")
            == "negado",
        )
    )

    operacao_sem_alvo = consulta.consultar(
        "componente"
    )

    resultados.append(
        assert_passou(
            "10. operação que exige alvo sem alvo é negada",
            operacao_sem_alvo.get("sucesso")
            is False
            and operacao_sem_alvo.get("estado")
            == "negado",
        )
    )

    # A porta interna recebe um objeto de autorrepresentação
    # explicitamente. Ela não abre a planta por conta própria.
    resultados.append(
        assert_passou(
            "11. fonte da consulta interna é a autorrepresentação",
            consulta.autorrepresentacao is autor,
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "12. consultas internas não modificam a planta",
            hash_antes == hash_depois,
        )
    )

    resultados.append(
        assert_passou(
            "13. consulta interna não inicia conversação",
            consulta.consultar(
                "conversar"
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "14. consulta interna não executa capacidades",
            not hasattr(
                consulta,
                "executar_capacidade",
            ),
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
