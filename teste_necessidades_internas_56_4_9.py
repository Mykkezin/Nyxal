#!/usr/bin/env python3

"""
NIXAL — TESTE DAS NECESSIDADES INTERNAS

Microetapa 56.4.9

Valida a transformação de achados do diagnóstico em
necessidades internas estruturadas, sem executar ações.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_diagnostico_autorreprentacao import (
    DiagnosticoAutorreprentacaoNixal,
)
from nixal_necessidades_internas import (
    NecessidadesInternasNixal,
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
    diagnostico = DiagnosticoAutorreprentacaoNixal()

    necessidades = NecessidadesInternasNixal(
        diagnostico=diagnostico
    )

    resultados: list[bool] = []

    hash_antes = hash_planta()

    resultado_diagnostico = diagnostico.diagnosticar()
    resultado = necessidades.analisar()
    valor = resultado.get("valor", {})
    lista = valor.get("necessidades", [])

    resultados.append(
        assert_passou(
            "1. análise de necessidades retorna sucesso",
            resultado.get("sucesso") is True,
        )
    )

    resultados.append(
        assert_passou(
            "2. diagnóstico atual é reconhecido como incompleto",
            resultado.get("valor", {}).get(
                "diagnostico_estado"
            )
            == "incompleto",
        )
    )

    resultados.append(
        assert_passou(
            "3. necessidades são retornadas em lista",
            isinstance(lista, list),
        )
    )

    resultados.append(
        assert_passou(
            "4. existe necessidade para a lacuna atual",
            any(
                item.get("problema")
                == "dependencias_arquiteturais_nao_declaradas"
                for item in lista
                if isinstance(item, dict)
            ),
        )
    )

    necessidade_dependencias = next(
        (
            item
            for item in lista
            if isinstance(item, dict)
            and item.get("problema")
            == "dependencias_arquiteturais_nao_declaradas"
        ),
        None,
    )

    resultados.append(
        assert_passou(
            "5. necessidade de dependências tem tipo correto",
            isinstance(
                necessidade_dependencias,
                dict,
            )
            and necessidade_dependencias.get("tipo")
            == "conhecimento_arquitetural",
        )
    )

    resultados.append(
        assert_passou(
            "6. necessidade de dependências tem nome formal",
            isinstance(
                necessidade_dependencias,
                dict,
            )
            and necessidade_dependencias.get(
                "necessidade"
            )
            == "conhecer_dependencias_arquiteturais",
        )
    )

    resultados.append(
        assert_passou(
            "7. necessidade preserva a origem do diagnóstico",
            isinstance(
                necessidade_dependencias,
                dict,
            )
            and necessidade_dependencias.get("origem")
            == "diagnostico_autorreprentacao",
        )
    )

    resultados.append(
        assert_passou(
            "8. necessidade não inventa uma solução",
            isinstance(
                necessidade_dependencias,
                dict,
            )
            and "solucao" not in necessidade_dependencias
            and "codigo" not in necessidade_dependencias,
        )
    )

    resultados.append(
        assert_passou(
            "9. diagnóstico original permanece disponível",
            resultado_diagnostico.get("estado")
            == "incompleto",
        )
    )

    # ------------------------------------------------------------
    # TESTE DE INCONSISTÊNCIA ISOLADA
    # ------------------------------------------------------------

    class DiagnosticoFalso:
        def diagnosticar(self) -> dict[str, object]:
            return {
                "sucesso": True,
                "estado": "inconsistente",
                "origem": "teste",
                "valor": {
                    "inconsistencias": [
                        "regra_de_modificacao_da_planta_insegura"
                    ],
                    "lacunas": [],
                    "achados": [],
                },
            }

    necessidade_inconsistencia = NecessidadesInternasNixal(
        diagnostico=DiagnosticoFalso()
    ).analisar()

    lista_inconsistencia = necessidade_inconsistencia.get(
        "valor",
        {},
    ).get(
        "necessidades",
        [],
    )

    item_inconsistencia = (
        lista_inconsistencia[0]
        if lista_inconsistencia
        else {}
    )

    resultados.append(
        assert_passou(
            "10. inconsistência gera necessidade",
            item_inconsistencia.get(
                "necessidade"
            )
            == "investigar_inconsistencia",
        )
    )

    resultados.append(
        assert_passou(
            "11. inconsistência recebe prioridade alta",
            item_inconsistencia.get(
                "prioridade"
            )
            == "alta",
        )
    )

    executar = necessidades.executar_necessidade(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "12. camada não executa a necessidade",
            executar.get("estado")
            == "negado",
        )
    )

    modificar = necessidades.modificar(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "13. camada não modifica a arquitetura",
            modificar.get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "14. camada usa o diagnóstico recebido",
            necessidades.diagnostico is diagnostico,
        )
    )

    resultados.append(
        assert_passou(
            "15. camada não acessa a planta diretamente",
            not hasattr(
                necessidades,
                "caminho_planta",
            ),
        )
    )

    resultados.append(
        assert_passou(
            "16. camada não executa capacidades",
            not hasattr(
                necessidades,
                "executar_capacidade",
            ),
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "17. análise não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    resultado_2 = necessidades.analisar()

    resultados.append(
        assert_passou(
            "18. análise é determinística",
            resultado == resultado_2,
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
