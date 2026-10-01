#!/usr/bin/env python3

"""
NIXAL — TESTE DA FORMULAÇÃO DE HIPÓTESES

Microetapa 56.4.12

Valida que evidências geram uma hipótese provisória,
sem confirmação automática ou alteração permanente.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_formulacao_hipoteses import (
    FormulacaoHipotesesNixal,
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
    formulador = FormulacaoHipotesesNixal()

    investigacao = {
        "necessidade": "conhecer_dependencias_arquiteturais",
        "pergunta": (
            "Quais relações de dependência existem entre os "
            "componentes da minha arquitetura?"
        ),
        "tipo_investigacao": "mapeamento_arquitetural",
        "valor": {
            "evidencias": [
                {
                    "fonte": "listar_arquivos",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "argumentos": {},
                },
                {
                    "fonte": "ler_arquivo",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "argumentos": {
                        "arquivo": "corpo_nixal.py"
                    },
                },
            ]
        },
    }

    resultados: list[bool] = []

    hash_antes = hash_planta()

    resultado = formulador.formular(
        investigacao
    )

    resultados.append(
        assert_passou(
            "1. formulação retorna sucesso",
            resultado.get("sucesso") is True,
        )
    )

    resultados.append(
        assert_passou(
            "2. hipótese é provisória",
            resultado.get("estado")
            == "hipotese_provisoria",
        )
    )

    valor = resultado.get(
        "valor",
        {}
    )

    resultados.append(
        assert_passou(
            "3. hipótese possui texto",
            isinstance(
                valor.get("hipotese"),
                str,
            )
            and bool(
                valor.get(
                    "hipotese",
                    "",
                ).strip()
            ),
        )
    )

    resultados.append(
        assert_passou(
            "4. hipótese preserva a pergunta",
            valor.get("pergunta")
            == investigacao["pergunta"],
        )
    )

    resultados.append(
        assert_passou(
            "5. hipótese preserva a necessidade",
            valor.get("necessidade")
            == investigacao["necessidade"],
        )
    )

    resultados.append(
        assert_passou(
            "6. hipótese não é marcada como confirmada",
            valor.get("confirmada")
            is False,
        )
    )

    resultados.append(
        assert_passou(
            "7. hipótese ainda não foi testada",
            valor.get("testada")
            is False,
        )
    )

    resultados.append(
        assert_passou(
            "8. confiança permanece indeterminada",
            valor.get("confianca")
            == "indeterminada",
        )
    )

    resultados.append(
        assert_passou(
            "9. evidências de suporte são preservadas",
            len(
                valor.get(
                    "evidencias_de_suporte",
                    [],
                )
            )
            == 2,
        )
    )

    resultados.append(
        assert_passou(
            "10. evidências contrárias não são inventadas",
            valor.get(
                "evidencias_contrarias_conhecidas"
            )
            == []
            and valor.get(
                "contrarias_avaliadas"
            )
            is False,
        )
    )

    resultados.append(
        assert_passou(
            "11. hipótese não inventa resultados de teste",
            "resultado_teste" not in valor
            and "teste_sucesso" not in valor,
        )
    )

    resultados.append(
        assert_passou(
            "12. testar hipótese está bloqueado",
            formulador.testar_hipotese(
                valor
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "13. confirmação está bloqueada",
            formulador.confirmar_hipotese(
                valor
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "14. incorporação permanente está bloqueada",
            formulador.incorporar_conhecimento(
                valor
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "15. modificação da arquitetura está bloqueada",
            formulador.modificar(
                valor
            ).get("estado")
            == "negado",
        )
    )

    resultado_sem_evidencia = formulador.formular(
        {
            "necessidade": "teste",
            "pergunta": "O que está acontecendo?",
            "valor": {
                "evidencias": []
            },
        }
    )

    resultados.append(
        assert_passou(
            "16. sem evidência suficiente não há hipótese",
            resultado_sem_evidencia.get(
                "estado"
            )
            == "desconhecido",
        )
    )

    resultado_evidencia_invalida = formulador.formular(
        {
            "necessidade": "teste",
            "pergunta": "O que está acontecendo?",
            "valor": {
                "evidencias": [
                    {
                        "fonte": "teste",
                        "sucesso": False,
                        "estado": "falha_fonte",
                    }
                ]
            },
        }
    )

    resultados.append(
        assert_passou(
            "17. falha de fonte não vira evidência",
            resultado_evidencia_invalida.get(
                "estado"
            )
            == "desconhecido",
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "18. formulação não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    resultado_2 = formulador.formular(
        investigacao
    )

    resultados.append(
        assert_passou(
            "19. formulação é determinística",
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
