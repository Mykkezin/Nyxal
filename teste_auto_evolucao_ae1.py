#!/usr/bin/env python3
"""
NYXAL — TESTE AE1
Auto-evolution governada: descoberta e preparação somente.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_auto_evolucao import AutoEvolucaoGovernadaNixOS


BASE_DIR = Path(__file__).resolve().parent
MODULO = BASE_DIR / "nixal_auto_evolucao.py"
RESIDENTE = BASE_DIR / "nixal_ciclo_residente.py"
LAUNCHER = BASE_DIR / "executar_nyxos_residente.py"

TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


def ciclo_falso() -> dict:
    return {
        "sucesso": True,
        "estado": "ciclo_concluido",
        "ciclo_id": "ciclo-ae1-001",
        "valor": {
            "necessidade_prioritaria": {
                "selecionada": {
                    "problema": "dependencia_arquitetural_nao_declarada",
                    "necessidade": "conhecer_dependencias",
                    "tipo": "conhecimento_arquitetural",
                    "prioridade": "baixa",
                }
            },
            "hipotese": {
                "estado_atual": "provisoria",
                "hipotese": (
                    "Representar relações de dependência pode reduzir "
                    "a lacuna arquitetural observada."
                )
            },
        },
    }


def main() -> None:
    verificar(MODULO.exists(), "módulo AE1 existe")
    verificar(RESIDENTE.exists(), "residente existe")
    verificar(LAUNCHER.exists(), "launcher existe")

    texto_modulo = MODULO.read_text(encoding="utf-8")
    texto_residente = RESIDENTE.read_text(encoding="utf-8")

    verificar(
        "AutoEvolucaoGovernadaNixOS" in texto_residente
        and "auto_evolucao_ae1" in texto_residente,
        "AE1 está conectado ao residente",
    )

    verificar(
        all(
            proibido not in texto_modulo
            for proibido in (
                "subprocess.",
                "os.system(",
                "Popen(",
                "git ",
                "exec(",
            )
        ),
        "AE1 não executa comandos ou candidatos",
    )

    verificar(
        "integracao_executada" in texto_modulo
        and "autorizacao_explicita" in texto_modulo,
        "AE1 declara explicitamente seus gates",
    )

    with tempfile.TemporaryDirectory(prefix="nyxal-ae1-") as pasta:
        auto = AutoEvolucaoGovernadaNixOS(
            BASE_DIR,
            diretorio_oportunidades=Path(pasta),
        )

        primeiro = auto.avaliar_ciclo(ciclo_falso())

        verificar(
            primeiro.get("sucesso") is True
            and primeiro.get("estado") == "oportunidade_criada"
            and primeiro.get("oportunidade_criada") is True,
            "AE1 identifica e registra uma oportunidade",
        )

        oportunidade = primeiro.get("valor", {})
        verificar(
            oportunidade.get("estado") == "oportunidade"
            and oportunidade.get("ciclo_origem") == "ciclo-ae1-001",
            "oportunidade preserva origem e estado",
        )

        verificar(
            oportunidade.get("autorizacao_explicita") is False
            and oportunidade.get("integracao_executada") is False
            and oportunidade.get("arquitetura_modificada") is False,
            "oportunidade não concede autoridade de integração",
        )

        segundo = auto.avaliar_ciclo(ciclo_falso())

        verificar(
            segundo.get("estado") == "oportunidade_ja_registrada"
            and segundo.get("oportunidade_criada") is False,
            "mesma oportunidade não é duplicada",
        )

        listar = auto.listar()
        verificar(
            len(listar) == 1
            and listar[0].get("oportunidade_id")
            == oportunidade.get("oportunidade_id"),
            "oportunidade pode ser consultada após persistência",
        )

        contexto = auto.contexto()
        verificar(
            contexto.get("descoberta_habilitada") is True
            and contexto.get("execucao_experimental_automatica") is False
            and contexto.get("autorizacao_explicita") is False,
            "AE1 permanece descoberta/preparação, sem execução automática",
        )

        arquivo = Path(pasta) / f"{oportunidade['oportunidade_id']}.json"
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        verificar(
            dados.get("proxima_etapa") == "avaliacao_e_preparacao_formal",
            "próxima etapa permanece preparação formal governada",
        )

    print()
    print("=" * 64)
    print("TESTE — AUTO-EVOLUTION GOVERNADA AE1")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
