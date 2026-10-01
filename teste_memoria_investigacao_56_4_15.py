#!/usr/bin/env python3

"""
NIXAL — TESTE DA MEMÓRIA PERSISTENTE DE INVESTIGAÇÃO

Microetapa 56.4.15

Valida persistência, recuperação, deduplicação e separação
da memória em relação à planta arquitetural.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from nixal_ciclo_vida_hipotese import (
    ESTADO_PROVISORIA,
    ESTADO_SUPORTADA,
    CicloVidaHipoteseNixal,
)
from nixal_memoria_investigacao import (
    MemoriaInvestigacaoNixal,
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
    resultados: list[bool] = []

    hash_antes = hash_planta()

    with tempfile.TemporaryDirectory() as diretorio:
        arquivo_memoria = (
            Path(diretorio)
            / "memoria_investigacao_nixal.json"
        )

        memoria = MemoriaInvestigacaoNixal(
            caminho=arquivo_memoria
        )

        ciclo = CicloVidaHipoteseNixal()

        iniciado = ciclo.iniciar(
            {
                "hipotese": (
                    "É possível que uma dependência ainda "
                    "não esteja formalizada."
                ),
                "estado": ESTADO_PROVISORIA,
                "necessidade": (
                    "conhecer_dependencias_arquiteturais"
                ),
            }
        )

        testado = ciclo.registrar_teste(
            iniciado["valor"],
            {
                "estado": "teste_concluido",
                "suporte": True,
                "contraria": False,
                "inconclusivo": False,
                "evidencias": [
                    {
                        "fonte": "teste_controlado"
                    }
                ],
            },
        )

        avaliado = ciclo.registrar_avaliacao(
            testado["valor"],
            {
                "estado": ESTADO_SUPORTADA,
                "motivo": (
                    "Evidência favorável."
                ),
            },
        )

        ciclo_final = avaliado["valor"]

        persistido = memoria.registrar(
            ciclo_final
        )

        resultados.append(
            assert_passou(
                "1. ciclo é persistido",
                persistido.get("estado")
                == "persistido",
            )
        )

        resultados.append(
            assert_passou(
                "2. arquivo de memória é criado",
                arquivo_memoria.exists(),
            )
        )

        resultados.append(
            assert_passou(
                "3. memória possui um registro",
                memoria.quantidade()
                == 1,
            )
        )

        registro = persistido.get(
            "valor",
            {},
        )

        registro_id = registro.get(
            "id"
        )

        resultados.append(
            assert_passou(
                "4. registro possui ID determinístico",
                isinstance(
                    registro_id,
                    str,
                )
                and len(registro_id)
                == 64,
            )
        )

        resultados.append(
            assert_passou(
                "5. ciclo completo é preservado",
                registro.get(
                    "ciclo",
                    {},
                ).get(
                    "estado_atual"
                )
                == ESTADO_SUPORTADA
                and len(
                    registro.get(
                        "ciclo",
                        {},
                    ).get(
                        "testes",
                        [],
                    )
                )
                == 1
                and len(
                    registro.get(
                        "ciclo",
                        {},
                    ).get(
                        "avaliacoes",
                        [],
                    )
                )
                == 1,
            )
        )

        duplicado = memoria.registrar(
            ciclo_final
        )

        resultados.append(
            assert_passou(
                "6. registro duplicado não é duplicado",
                duplicado.get("estado")
                == "ja_existente"
                and memoria.quantidade()
                == 1,
            )
        )

        memoria_nova = MemoriaInvestigacaoNixal(
            caminho=arquivo_memoria
        )

        resultados.append(
            assert_passou(
                "7. nova instância recupera a memória",
                memoria_nova.quantidade()
                == 1,
            )
        )

        recuperado = memoria_nova.obter(
            registro_id
        )

        resultados.append(
            assert_passou(
                "8. registro recuperado é idêntico",
                recuperado == registro,
            )
        )

        listado = memoria_nova.listar()

        resultados.append(
            assert_passou(
                "9. listagem retorna registro persistido",
                len(listado)
                == 1
                and listado[0]
                == registro,
            )
        )

        recarregado = memoria_nova.recarregar()

        resultados.append(
            assert_passou(
                "10. recarregamento preserva quantidade",
                recarregado.get("estado")
                == "recarregado"
                and recarregado.get(
                    "valor",
                    {},
                ).get("quantidade")
                == 1,
            )
        )

        invalido = memoria_nova.registrar(
            {
                "hipotese": "inválida",
                "estado_atual": "provisoria",
                "historico": [],
                "testes": [],
                "avaliacoes": [],
                "conhecimento_permanente": True,
            }
        )

        resultados.append(
            assert_passou(
                "11. memória rejeita conhecimento permanente",
                invalido.get("estado")
                == "negado",
            )
        )

        ausente = memoria_nova.obter(
            "0" * 64
        )

        resultados.append(
            assert_passou(
                "12. registro inexistente retorna None",
                ausente is None,
            )
        )

        capacidade = memoria_nova.executar_capacidade(
            "teste"
        )

        resultados.append(
            assert_passou(
                "13. memória não executa capacidades",
                capacidade.get("estado")
                == "negado",
            )
        )

        arquitetura = memoria_nova.modificar_arquitetura(
            "teste"
        )

        resultados.append(
            assert_passou(
                "14. memória não modifica arquitetura",
                arquitetura.get("estado")
                == "negado",
            )
        )

        promover = memoria_nova.promover_conhecimento(
            registro
        )

        resultados.append(
            assert_passou(
                "15. memória não promove conhecimento",
                promover.get("estado")
                == "negado",
            )
        )

        arquivo_json = (
            arquivo_memoria.read_text(
                encoding="utf-8"
            )
        )

        resultados.append(
            assert_passou(
                "16. memória persistida é JSON válido",
                arquivo_json.strip().startswith("{")
                and '"registros"' in arquivo_json,
            )
        )

        resultados.append(
            assert_passou(
                "17. memória mantém versão própria",
                registro.get(
                    "versao_memoria"
                )
                == "56.4.15",
            )
        )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "18. memória não modifica a planta",
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
