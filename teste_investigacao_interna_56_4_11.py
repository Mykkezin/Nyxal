#!/usr/bin/env python3

"""
NIXAL — TESTE DA INVESTIGAÇÃO INTERNA

Microetapa 56.4.11

Valida coleta controlada de evidências sem transformar evidência
em hipótese ou conhecimento permanente.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_autorreprentacao import AutorreprentacaoNixal
from nixal_capacidades import GerenciadorCapacidades
from nixal_investigacao_interna import (
    InvestigacaoInternaNixal,
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

    gerenciador = GerenciadorCapacidades()

    investigador = InvestigacaoInternaNixal(
        gerenciador=gerenciador,
        autorrepresentacao=autor,
    )

    investigacao = {
        "necessidade": "conhecer_dependencias_arquiteturais",
        "pergunta": (
            "Quais relações de dependência existem entre os "
            "componentes da minha arquitetura?"
        ),
        "tipo_investigacao": "mapeamento_arquitetural",
    }

    resultados: list[bool] = []

    hash_antes = hash_planta()

    resultado = investigador.executar(
        investigacao
    )

    valor = resultado.get(
        "valor",
        {}
    )

    evidencias = valor.get(
        "evidencias",
        []
    )

    resultados.append(
        assert_passou(
            "1. investigação retorna sucesso",
            resultado.get("sucesso") is True,
        )
    )

    resultados.append(
        assert_passou(
            "2. evidência é coletada",
            resultado.get("estado")
            == "evidencia_coletada"
            and isinstance(
                evidencias,
                list,
            )
            and len(evidencias) >= 1,
        )
    )

    resultados.append(
        assert_passou(
            "3. pergunta é preservada",
            valor.get("pergunta")
            == investigacao["pergunta"],
        )
    )

    resultados.append(
        assert_passou(
            "4. tipo da investigação é preservado",
            valor.get("tipo_investigacao")
            == "mapeamento_arquitetural",
        )
    )

    resultados.append(
        assert_passou(
            "5. listar_arquivos é usada como fonte",
            "listar_arquivos"
            in valor.get(
                "fontes_utilizadas",
                [],
            ),
        )
    )

    resultados.append(
        assert_passou(
            "6. ler_arquivo é usada como fonte",
            "ler_arquivo"
            in valor.get(
                "fontes_utilizadas",
                [],
            ),
        )
    )

    fontes_reais = {
        item.get("fonte")
        for item in evidencias
        if isinstance(item, dict)
    }

    resultados.append(
        assert_passou(
            "7. fontes executadas pertencem ao conjunto permitido",
            fontes_reais.issubset(
                {
                    "listar_arquivos",
                    "ler_arquivo",
                }
            ),
        )
    )

    resultados.append(
        assert_passou(
            "8. investigação não produz conclusão automática",
            valor.get("conclusao") is None,
        )
    )

    resultados.append(
        assert_passou(
            "9. investigação não produz hipótese",
            valor.get("hipotese") is None,
        )
    )

    formular = investigador.formular_hipotese(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "10. hipótese é bloqueada nesta camada",
            formular.get("estado")
            == "negado",
        )
    )

    incorporar = investigador.incorporar_conhecimento(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "11. incorporação permanente é bloqueada",
            incorporar.get("estado")
            == "negado",
        )
    )

    modificar = investigador.modificar(
        "qualquer"
    )

    resultados.append(
        assert_passou(
            "12. modificação da arquitetura é bloqueada",
            modificar.get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "13. investigador usa autorrepresentação recebida",
            investigador.autorrepresentacao is autor,
        )
    )

    resultados.append(
        assert_passou(
            "14. investigador usa gerenciador recebido",
            investigador.gerenciador is gerenciador,
        )
    )

    resultados.append(
        assert_passou(
            "15. investigador não acessa a planta diretamente",
            not hasattr(
                investigador,
                "caminho_planta",
            ),
        )
    )

    resultados.append(
        assert_passou(
            "16. investigador não expõe execução arbitrária",
            not hasattr(
                investigador,
                "executar_capacidade",
            ),
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "17. investigação não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    resultado_2 = investigador.executar(
        investigacao
    )

    resultados.append(
        assert_passou(
            "18. estrutura da investigação é determinística",
            resultado_2.get("valor", {}).get(
                "pergunta"
            )
            == valor.get("pergunta")
            and resultado_2.get("valor", {}).get(
                "tipo_investigacao"
            )
            == valor.get("tipo_investigacao")
            and resultado_2.get("valor", {}).get(
                "fontes_utilizadas"
            )
            == valor.get("fontes_utilizadas"),
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
