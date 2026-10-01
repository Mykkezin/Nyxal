#!/usr/bin/env python3

"""
NIXAL — TESTE DA FORMULAÇÃO DE INVESTIGAÇÃO

Microetapa 56.4.10

Valida que necessidades internas viram perguntas estruturadas,
sem execução de investigação, sem hipóteses automáticas e sem
modificação da arquitetura.
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
from nixal_formulacao_investigacao import (
    FormulacaoInvestigacaoNixal,
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

    formulacao = FormulacaoInvestigacaoNixal(
        necessidades=necessidades
    )

    resultados: list[bool] = []

    hash_antes = hash_planta()

    resultado = formulacao.formular()

    resultados.append(
        assert_passou(
            "1. formulação retorna sucesso",
            resultado.get("sucesso") is True,
        )
    )

    valor = resultado.get("valor", {})
    investigacoes = valor.get(
        "investigacoes",
        [],
    )

    resultados.append(
        assert_passou(
            "2. existe investigação formulada",
            isinstance(
                investigacoes,
                list,
            )
            and len(investigacoes) >= 1,
        )
    )

    dependencias = next(
        (
            item
            for item in investigacoes
            if isinstance(item, dict)
            and item.get("necessidade")
            == "conhecer_dependencias_arquiteturais"
        ),
        None,
    )

    resultados.append(
        assert_passou(
            "3. necessidade atual gera investigação correta",
            isinstance(
                dependencias,
                dict,
            )
            and dependencias.get("estado")
            == "formulada",
        )
    )

    resultados.append(
        assert_passou(
            "4. pergunta de investigação é explícita",
            isinstance(
                dependencias,
                dict,
            )
            and "Quais relações de dependência"
            in dependencias.get(
                "pergunta",
                "",
            ),
        )
    )

    resultados.append(
        assert_passou(
            "5. tipo da investigação é arquitetural",
            isinstance(
                dependencias,
                dict,
            )
            and dependencias.get(
                "tipo_investigacao"
            )
            == "mapeamento_arquitetural",
        )
    )

    resultados.append(
        assert_passou(
            "6. evidência necessária é declarada",
            isinstance(
                dependencias,
                dict,
            )
            and isinstance(
                dependencias.get(
                    "evidencia_necessaria"
                ),
                str,
            )
            and bool(
                dependencias.get(
                    "evidencia_necessaria",
                    "",
                ).strip()
            ),
        )
    )

    resultados.append(
        assert_passou(
            "7. formulação preserva origem das necessidades",
            isinstance(
                dependencias,
                dict,
            )
            and dependencias.get(
                "origem"
            )
            == "necessidades_internas_nixal",
        )
    )

    resultados.append(
        assert_passou(
            "8. pergunta não é uma ação",
            isinstance(
                dependencias,
                dict,
            )
            and "executar" not in dependencias.get(
                "pergunta",
                "",
            ).lower(),
        )
    )

    resultados.append(
        assert_passou(
            "9. formulação não cria hipótese",
            "hipotese" not in dependencias
            and "hipótese" not in dependencias,
        )
    )

    executar = formulacao.executar_investigacao(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "10. investigação não é executada nesta camada",
            executar.get("estado")
            == "negado",
        )
    )

    hipotese = formulacao.gerar_hipotese(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "11. hipótese ainda não é gerada",
            hipotese.get("estado")
            == "negado",
        )
    )

    modificar = formulacao.modificar(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "12. camada não modifica a arquitetura",
            modificar.get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "13. camada usa as necessidades recebidas",
            formulacao.necessidades
            is necessidades,
        )
    )

    resultados.append(
        assert_passou(
            "14. camada não acessa a planta diretamente",
            not hasattr(
                formulacao,
                "caminho_planta",
            ),
        )
    )

    resultados.append(
        assert_passou(
            "15. camada não executa capacidades",
            not hasattr(
                formulacao,
                "executar_capacidade",
            ),
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "16. formulação não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    resultado_2 = formulacao.formular()

    resultados.append(
        assert_passou(
            "17. formulação é determinística",
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
