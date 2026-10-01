#!/usr/bin/env python3

"""
NIXAL — TESTE DO DIAGNÓSTICO DA AUTORREPRESENTAÇÃO

Microetapa 56.4.8

Valida que o diagnóstico consegue reconhecer o estado atual
da autorrepresentação sem modificar a arquitetura.
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
    EstadoConhecimentoNixal,
)
from nixal_diagnostico_autorreprentacao import (
    ESTADO_INCOMPLETO,
    ESTADO_INCONSISTENTE,
    DiagnosticoAutorreprentacaoNixal,
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

    diagnostico = DiagnosticoAutorreprentacaoNixal(
        estado=estado
    )

    resultados: list[bool] = []

    hash_antes = hash_planta()

    resultado = diagnostico.diagnosticar()

    resultados.append(
        assert_passou(
            "1. diagnóstico retorna sucesso",
            resultado.get("sucesso") is True,
        )
    )

    resultados.append(
        assert_passou(
            "2. diagnóstico reconhece a autorrepresentação como incompleta",
            resultado.get("estado")
            == ESTADO_INCOMPLETO,
        )
    )

    valor = resultado.get("valor")

    resultados.append(
        assert_passou(
            "3. diagnóstico retorna estrutura de achados",
            isinstance(valor, dict)
            and isinstance(
                valor.get("achados"),
                list,
            )
            and isinstance(
                valor.get("lacunas"),
                list,
            )
            and isinstance(
                valor.get("inconsistencias"),
                list,
            ),
        )
    )

    resultados.append(
        assert_passou(
            "4. dependências não declaradas são tratadas como lacuna",
            "dependencias_arquiteturais_nao_declaradas"
            in valor.get("lacunas", []),
        )
    )

    resultados.append(
        assert_passou(
            "5. ausência de dependências não vira inconsistência",
            "dependencias_arquiteturais_nao_declaradas"
            not in valor.get("inconsistencias", []),
        )
    )

    resultados.append(
        assert_passou(
            "6. não há inconsistência na regra da planta",
            "regra_de_modificacao_da_planta_insegura"
            not in valor.get("inconsistencias", []),
        )
    )

    resultados.append(
        assert_passou(
            "7. identidade atual está disponível",
            "identidade_nao_disponivel"
            not in valor.get("lacunas", []),
        )
    )

    resultados.append(
        assert_passou(
            "8. componentes atuais estão disponíveis",
            "componentes_nao_disponiveis"
            not in valor.get("lacunas", []),
        )
    )

    resultados.append(
        assert_passou(
            "9. capacidades atuais estão disponíveis",
            "capacidades_nao_disponiveis"
            not in valor.get("lacunas", []),
        )
    )

    resultados.append(
        assert_passou(
            "10. limites atuais estão disponíveis",
            "limites_nao_disponiveis"
            not in valor.get("lacunas", []),
        )
    )

    resultados.append(
        assert_passou(
            "11. regras atuais estão disponíveis",
            "regras_modificacao_nao_disponiveis"
            not in valor.get("lacunas", []),
        )
    )

    resultados.append(
        assert_passou(
            "12. diagnóstico usa o estado composto",
            diagnostico.estado is estado,
        )
    )

    resultados.append(
        assert_passou(
            "13. diagnóstico não acessa a planta diretamente",
            not hasattr(
                diagnostico,
                "caminho_planta",
            ),
        )
    )

    resultados.append(
        assert_passou(
            "14. diagnóstico não executa capacidades",
            not hasattr(
                diagnostico,
                "executar_capacidade",
            ),
        )
    )

    # ------------------------------------------------------------
    # TESTE ISOLADO DE INCONSISTÊNCIA
    # ------------------------------------------------------------

    class EstadoFalso:
        def construir(self) -> dict[str, object]:
            return {
                "sucesso": True,
                "estado": "conhecido",
                "origem": "teste",
                "valor": {
                    "identidade": {
                        "estado": "conhecido",
                        "valor": {
                            "nome": "Nixal",
                            "versao_arquitetura": "56.4.2",
                        },
                    },
                    "estado_arquitetura": {
                        "estado": "conhecido",
                        "valor": {
                            "fundacao": "em_construcao",
                            "camada_conversacional": "iniciada",
                            "autorrepresentacao": "em_construcao",
                            "evolucao_autonoma": "ainda_nao_iniciada",
                        },
                    },
                    "componentes": {
                        "estado": "conhecido",
                        "valor": [
                            {
                                "id": "teste",
                                "arquivo_principal": "teste.py",
                                "funcao": "teste",
                            }
                        ],
                    },
                    "capacidades": {
                        "estado": "conhecido",
                        "valor": ["teste"],
                    },
                    "limites": {
                        "estado": "conhecido",
                        "valor": ["teste"],
                    },
                    "regras_modificacao": {
                        "estado": "conhecido",
                        "valor": {
                            "planta": "somente_leitura",
                            "arquitetura": "somente_leitura",
                            "codigo_fundacional": "protegido",
                            "evolucoes_experimentais": "controlado",
                        },
                    },
                },
            }

    diagnostico_falso = DiagnosticoAutorreprentacaoNixal(
        estado=EstadoFalso()
    )

    resultado_falso = diagnostico_falso.diagnosticar()

    resultados.append(
        assert_passou(
            "15. diagnóstico detecta inconsistência explícita",
            resultado_falso.get("estado")
            == ESTADO_INCONSISTENTE,
        )
    )

    resultados.append(
        assert_passou(
            "16. inconsistência aparece nos achados",
            "camada_conversacional_contradiz_estado_da_planta"
            in resultado_falso.get(
                "valor",
                {},
            ).get(
                "inconsistencias",
                [],
            ),
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "17. diagnóstico não modifica a planta",
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
