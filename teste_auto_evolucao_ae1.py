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


def ciclo_sem_hipotese(ciclo_id: str) -> dict:
    return {
        "sucesso": True,
        "estado": "ciclo_concluido",
        "ciclo_id": ciclo_id,
        "valor": {
            "necessidade_prioritaria": {
                "selecionada": {
                    "origem": "diagnostico_autorreprentacao",
                    "problema": "componentes_nao_disponiveis",
                    "tipo_problema": "lacuna",
                    "tipo": "conhecimento_arquitetural",
                    "necessidade": "conhecer_componentes",
                    "prioridade": "alta",
                    "motivo": "O diagnóstico observou uma lacuna explícita.",
                }
            },
            "hipotese": None,
        },
    }


def testar_hipotese_provisoria_automatica_e_deduplicacao() -> None:
    with tempfile.TemporaryDirectory(prefix="nyxal-ae1-adaptativa-") as pasta:
        auto = AutoEvolucaoGovernadaNixOS(
            BASE_DIR,
            diretorio_oportunidades=Path(pasta),
        )

        primeiro = auto.avaliar_ciclo(ciclo_sem_hipotese("ciclo-adaptativo-001"))
        oportunidade = primeiro.get("valor", {})

        verificar(
            primeiro.get("estado") == "oportunidade_criada"
            and primeiro.get("hipotese_auto_formulada") is True,
            "AE1 formula hipótese provisória quando a necessidade real não traz hipótese",
        )
        verificar(
            oportunidade.get("hipotese_gerada_automaticamente") is True
            and oportunidade.get("estado_hipotese") == "provisoria"
            and "componentes_nao_disponiveis" in oportunidade.get("hipotese", ""),
            "hipótese automática cita o sinal observado e permanece provisória",
        )
        verificar(
            oportunidade.get("autorizacao_explicita") is False
            and oportunidade.get("integracao_executada") is False
            and oportunidade.get("arquitetura_modificada") is False,
            "a descoberta não executa nem integra uma alteração",
        )

        segundo = auto.avaliar_ciclo(ciclo_sem_hipotese("ciclo-adaptativo-002"))
        oportunidade_reforcada = segundo.get("valor", {})
        verificar(
            segundo.get("estado") == "oportunidade_reforcada"
            and segundo.get("oportunidade_criada") is False
            and segundo.get("observacao_atualizada") is True,
            "uma necessidade recorrente reforça a mesma oportunidade em vez de duplicá-la",
        )
        verificar(
            oportunidade_reforcada.get("observacoes_total") == 2
            and oportunidade_reforcada.get("ciclos_observados")
            == ["ciclo-adaptativo-001", "ciclo-adaptativo-002"],
            "a recorrência preserva contagem e proveniência dos ciclos",
        )

        repetido = auto.avaliar_ciclo(ciclo_sem_hipotese("ciclo-adaptativo-002"))
        verificar(
            repetido.get("estado") == "oportunidade_ja_registrada"
            and repetido.get("valor", {}).get("observacoes_total") == 2,
            "reprocessar o mesmo ciclo é idempotente",
        )
        verificar(
            len(list(Path(pasta).glob("oportunidade-*.json"))) == 1,
            "necessidades repetidas não criam dezenas de arquivos por ciclo",
        )


def testar_falha_residente_vira_hipotese_para_investigar() -> None:
    with tempfile.TemporaryDirectory(prefix="nyxal-ae1-falha-") as pasta:
        auto = AutoEvolucaoGovernadaNixOS(
            BASE_DIR,
            diretorio_oportunidades=Path(pasta),
        )
        resultado = auto.avaliar_ciclo({
            "sucesso": False,
            "estado": "erro",
            "ciclo_id": "ciclo-falha-001",
            "erro": "Falha observada ao concluir diagnóstico.",
        })
        oportunidade = resultado.get("valor", {})
        verificar(
            resultado.get("estado") == "oportunidade_criada"
            and resultado.get("hipotese_auto_formulada") is True,
            "falha operacional observada também vira proposta de investigação",
        )
        verificar(
            oportunidade.get("prioridade", {}).get("prioridade") == "alta"
            and "causa raiz" in oportunidade.get("hipotese", ""),
            "falha é tratada como sinal de alta prioridade, sem inventar causa raiz",
        )


def testar_sem_evidencia_nao_inventa_melhoria() -> None:
    with tempfile.TemporaryDirectory(prefix="nyxal-ae1-sem-evidencia-") as pasta:
        auto = AutoEvolucaoGovernadaNixOS(
            BASE_DIR,
            diretorio_oportunidades=Path(pasta),
        )
        resultado = auto.avaliar_ciclo({
            "sucesso": True,
            "estado": "ciclo_concluido",
            "ciclo_id": "ciclo-sem-sinal",
            "valor": {},
        })
        verificar(
            resultado.get("estado") == "sem_oportunidade"
            and resultado.get("oportunidade_criada") is False
            and not list(Path(pasta).glob("oportunidade-*.json")),
            "sem necessidade ou falha observada, AE1 não inventa uma oportunidade",
        )


def main() -> None:
    testar_hipotese_provisoria_automatica_e_deduplicacao()
    testar_falha_residente_vira_hipotese_para_investigar()
    testar_sem_evidencia_nao_inventa_melhoria()

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
            and contexto.get("hipotese_provisoria_por_necessidade_observada") is True
            and contexto.get("deduplicacao_de_necessidade_recorrente") is True,
            "AE1 expõe descoberta adaptativa e controle de recorrência",
        )
        verificar(
            contexto.get("execucao_experimental_automatica") is False
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
