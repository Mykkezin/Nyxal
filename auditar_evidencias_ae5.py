#!/usr/bin/env python3
"""Auditoria somente leitura do Gate de Evidências AE5.

Não executa ciclos, não cria sinais, não altera persistência e não concede
qualquer autorização. Serve para distinguir evidência operacional real de
validação determinística por testes.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MAX_CICLOS = 20
MIN_OBSERVACOES = 3
MIN_SUCESSOS = 2


def carregar(caminho: Path) -> dict[str, Any] | None:
    try:
        valor = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return valor if isinstance(valor, dict) else None


def normalizar(valor: Any) -> str:
    if not isinstance(valor, str):
        return ""
    return re.sub(r"\s+", " ", valor.strip().casefold())


def auditar(repositorio: Path, limite: int = 200) -> dict[str, Any]:
    externo = repositorio.resolve().parent
    diretorio_ae4 = externo / "Nyxal-evolution-ae4"
    diretorio_oportunidades = externo / "Nyxal-evolution-opportunities"

    auditorias = sorted(
        diretorio_ae4.glob("ae4-ciclo-*.json"),
        key=lambda p: p.stat().st_mtime,
    )[-limite:] if diretorio_ae4.is_dir() else []

    linhas: dict[tuple[str, str], dict[str, Any]] = {}
    ciclos_validos: set[str] = set()
    auditorias_validas = 0

    for caminho in auditorias:
        auditoria = carregar(caminho)
        if not auditoria:
            continue
        ciclo_id = auditoria.get("ciclo_id")
        etapas = auditoria.get("etapas")
        if not isinstance(ciclo_id, str) or not isinstance(etapas, list):
            continue

        etapa_ae1 = next(
            (e for e in etapas if isinstance(e, dict) and e.get("etapa") == "AE1"),
            None,
        )
        if not isinstance(etapa_ae1, dict):
            continue

        oportunidade_id = etapa_ae1.get("oportunidade_id")
        if not isinstance(oportunidade_id, str) or not oportunidade_id:
            continue

        oportunidade = carregar(
            diretorio_oportunidades / f"{oportunidade_id}.json"
        ) if diretorio_oportunidades.is_dir() else None
        if not oportunidade:
            continue

        limitacao = oportunidade.get("limitacao")
        hipotese = oportunidade.get("hipotese")
        if not isinstance(limitacao, str) or not isinstance(hipotese, str):
            continue

        sucesso = auditoria.get("estado") != "ae4_ae1_falhou"
        chave = (normalizar(limitacao), normalizar(hipotese))
        linha = linhas.setdefault(
            chave,
            {
                "limitacao": limitacao,
                "hipotese": hipotese,
                "ciclos": {},
            },
        )
        linha["ciclos"][ciclo_id] = {
            "oportunidade_id": oportunidade_id,
            "sucesso": bool(sucesso),
            "auditoria": caminho.name,
        }
        ciclos_validos.add(ciclo_id)
        auditorias_validas += 1

    resultados = []
    maduras = 0
    for linha in linhas.values():
        evidencias = list(linha["ciclos"].items())[-MAX_CICLOS:]
        sucessos = sum(1 for _, e in evidencias if e["sucesso"])
        observacoes = len(evidencias)
        madura = observacoes >= MIN_OBSERVACOES and sucessos >= MIN_SUCESSOS
        if madura:
            maduras += 1
        resultados.append({
            "limitacao": linha["limitacao"],
            "hipotese": linha["hipotese"],
            "ciclos_observados": [c for c, _ in evidencias],
            "observacoes": observacoes,
            "observacoes_sucesso": sucessos,
            "madura_pela_politica": madura,
        })

    resultados.sort(key=lambda item: (-item["observacoes"], item["hipotese"]))
    evidencia_real = bool(auditorias_validas)

    return {
        "gate": "AE5_EVIDENCIAS",
        "estado": "evidencia_observacional_encontrada" if evidencia_real else "sem_evidencia_operacional",
        "evidencia_operacional_encontrada": evidencia_real,
        "auditorias_ae4_validas": auditorias_validas,
        "ciclos_distintos": len(ciclos_validos),
        "linhas_avaliadas": len(resultados),
        "linhas_maduras": maduras,
        "linhas": resultados,
        "criterios": {
            "janela_ciclos": MAX_CICLOS,
            "min_observacoes": MIN_OBSERVACOES,
            "min_sucessos": MIN_SUCESSOS,
        },
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "stable_modificada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
        "somente_leitura": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita evidências operacionais reais da AE5.")
    parser.add_argument("--repositorio", type=Path, default=Path(__file__).resolve())
    parser.add_argument("--limite", type=int, default=200)
    args = parser.parse_args()

    if args.limite < 1:
        parser.error("--limite deve ser >= 1")

    resultado = auditar(args.repositorio, args.limite)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))

    return 0 if resultado["evidencia_operacional_encontrada"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
