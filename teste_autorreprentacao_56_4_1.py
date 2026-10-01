#!/usr/bin/env python3

"""
NIXAL — TESTE ISOLADO DE AUTORREPRESENTAÇÃO

Microetapa 56.4.1

Objetivo:

Definir e testar o contrato mínimo de leitura de uma representação
estrutural da própria Nixal antes da criação de planta_nixal/planta.json.

Este teste NÃO cria a planta real da Nixal.
Ele usa uma planta mínima em memória apenas para validar o comportamento
esperado do futuro leitor de autorrepresentação.

Princípios testados:

1. Consultar componentes declarados.
2. Consultar a função de um componente declarado.
3. Consultar dependências declaradas.
4. Consultar capacidades declaradas.
5. Consultar limitações declaradas.
6. Consultar regras de modificação declaradas.
7. Consultar a versão da arquitetura.
8. Recusar afirmações sobre informação ausente.
9. Diferenciar ausência de informação de informação declarada.
10. Nunca inventar um componente, capacidade ou sensor.
"""

from __future__ import annotations

import json
from typing import Any


PLANTA_TESTE = {
    "identidade": {
        "nome": "Nixal",
        "versao_arquitetura": "56.4.1-test",
        "proposito": "Modelo estrutural mínimo para testes de autorrepresentação.",
    },
    "arquitetura": {
        "componentes": [
            {
                "id": "corpo_computacional",
                "nome": "Corpo computacional",
                "funcao": "Representar e consultar o estado computacional da Nixal.",
            },
            {
                "id": "cristalizacao",
                "nome": "Cristalização",
                "funcao": "Representar conhecimento em estruturas compactas e reconstruíveis.",
            },
            {
                "id": "composicao",
                "nome": "Composição",
                "funcao": "Planejar e encadear ações e operações de contexto.",
            },
        ]
    },
    "dependencias": [
        {
            "origem": "composicao",
            "destino": "corpo_computacional",
            "tipo": "consulta",
        },
        {
            "origem": "composicao",
            "destino": "cristalizacao",
            "tipo": "integração",
        },
    ],
    "capacidades": [
        "obter_hora",
        "listar_arquivos",
        "ler_estado_corpo",
        "ler_memoria_corporal",
        "ler_arquivo",
    ],
    "limites": [
        "Não declarar como existente uma capacidade ausente da planta.",
        "Não declarar como conhecido um componente ausente da planta.",
        "Não inferir sensores físicos não declarados.",
    ],
    "regras_modificacao": {
        "modo_atual": "somente_leitura",
        "pode_modificar_planta": False,
        "pode_modificar_codigo": False,
    },
}


def normalizar(texto: str) -> str:
    return " ".join(texto.lower().strip().split())


def buscar_componente(planta: dict[str, Any], identificador: str) -> dict[str, Any] | None:
    alvo = normalizar(identificador)

    for componente in planta.get("arquitetura", {}).get("componentes", []):
        if normalizar(str(componente.get("id", ""))) == alvo:
            return componente

        if normalizar(str(componente.get("nome", ""))) == alvo:
            return componente

    return None


def listar_dependencias(planta: dict[str, Any], componente: str) -> list[dict[str, Any]]:
    alvo = normalizar(componente)
    dependencias: list[dict[str, Any]] = []

    for item in planta.get("dependencias", []):
        origem = normalizar(str(item.get("origem", "")))
        destino = normalizar(str(item.get("destino", "")))

        if alvo in (origem, destino):
            dependencias.append(item)

    return dependencias


def consultar(planta: dict[str, Any], consulta: dict[str, Any]) -> dict[str, Any]:
    tipo = consulta.get("tipo")

    if tipo == "identidade":
        identidade = planta.get("identidade")
        if not isinstance(identidade, dict):
            return {"sucesso": False, "estado": "desconhecido"}
        return {"sucesso": True, "estado": "conhecido", "valor": identidade}

    if tipo == "componentes":
        componentes = planta.get("arquitetura", {}).get("componentes")
        if not isinstance(componentes, list):
            return {"sucesso": False, "estado": "desconhecido"}
        return {"sucesso": True, "estado": "conhecido", "valor": componentes}

    if tipo == "funcao_componente":
        componente = buscar_componente(
            planta,
            str(consulta.get("componente", "")),
        )
        if componente is None:
            return {
                "sucesso": True,
                "estado": "desconhecido",
                "valor": None,
            }

        return {
            "sucesso": True,
            "estado": "conhecido",
            "valor": componente.get("funcao"),
        }

    if tipo == "dependencias":
        componente = str(consulta.get("componente", ""))
        encontrado = buscar_componente(planta, componente)
        if encontrado is None:
            return {
                "sucesso": True,
                "estado": "desconhecido",
                "valor": None,
            }

        return {
            "sucesso": True,
            "estado": "conhecido",
            "valor": listar_dependencias(planta, componente),
        }

    if tipo == "capacidades":
        capacidades = planta.get("capacidades")
        if not isinstance(capacidades, list):
            return {"sucesso": False, "estado": "desconhecido"}
        return {"sucesso": True, "estado": "conhecido", "valor": capacidades}

    if tipo == "limites":
        limites = planta.get("limites")
        if not isinstance(limites, list):
            return {"sucesso": False, "estado": "desconhecido"}
        return {"sucesso": True, "estado": "conhecido", "valor": limites}

    if tipo == "regras_modificacao":
        regras = planta.get("regras_modificacao")
        if not isinstance(regras, dict):
            return {"sucesso": False, "estado": "desconhecido"}
        return {"sucesso": True, "estado": "conhecido", "valor": regras}

    if tipo == "versao":
        identidade = planta.get("identidade", {})
        if not isinstance(identidade, dict):
            return {"sucesso": False, "estado": "desconhecido"}

        versao = identidade.get("versao_arquitetura")
        if not isinstance(versao, str) or not versao.strip():
            return {"sucesso": True, "estado": "desconhecido", "valor": None}

        return {"sucesso": True, "estado": "conhecido", "valor": versao}

    return {
        "sucesso": True,
        "estado": "desconhecido",
        "valor": None,
    }


def executar_teste(nome: str, consulta: dict[str, Any], estado_esperado: str) -> bool:
    resultado = consultar(PLANTA_TESTE, consulta)
    passou = resultado.get("estado") == estado_esperado

    print(f"[{'PASS' if passou else 'FAIL'}] {nome}")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print()

    return passou


def main() -> None:
    print("=" * 68)
    print("NIXAL — AUTORREPRESENTAÇÃO 56.4.1")
    print("TESTE ISOLADO DO CONTRATO DE LEITURA")
    print("=" * 68)
    print()

    resultados = []

    resultados.append(
        executar_teste(
            "Identidade conhecida",
            {"tipo": "identidade"},
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Lista de componentes conhecida",
            {"tipo": "componentes"},
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Função de componente conhecida",
            {
                "tipo": "funcao_componente",
                "componente": "corpo_computacional",
            },
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Dependências de componente conhecidas",
            {
                "tipo": "dependencias",
                "componente": "composicao",
            },
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Capacidades conhecidas",
            {"tipo": "capacidades"},
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Limitações conhecidas",
            {"tipo": "limites"},
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Regras de modificação conhecidas",
            {"tipo": "regras_modificacao"},
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Versão da arquitetura conhecida",
            {"tipo": "versao"},
            "conhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Componente ausente não é inventado",
            {
                "tipo": "funcao_componente",
                "componente": "camera",
            },
            "desconhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Consulta não declarada não é inventada",
            {
                "tipo": "sensor_fisico",
                "sensor": "camera",
            },
            "desconhecido",
        )
    )

    resultados.append(
        executar_teste(
            "Capacidade ausente não é inventada",
            {
                "tipo": "capacidade_especifica",
                "capacidade": "visao_computacional",
            },
            "desconhecido",
        )
    )

    sucesso = all(resultados)

    print("=" * 68)
    print(f"TESTES PASSARAM: {sum(resultados)}/{len(resultados)}")
    print(f"PASSOU: {sucesso}")
    print("=" * 68)

    if not sucesso:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
