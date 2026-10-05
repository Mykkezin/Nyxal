#!/usr/bin/env python3
"""Testes do coletor dual governado de datasets AE5."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from nixal_coletor_dataset_dual_ae5 import ColetorDatasetDualAE5


class CicloFakeClock:
    def __init__(self) -> None:
        self.agora = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def agora_fn(self) -> datetime:
        return self.agora


def ciclo(ciclo_id: str, cpu: float = 20.0, aprendizado: str = "manter"):
    return {
        "sucesso": True,
        "estado": "ciclo_concluido",
        "ciclo_id": ciclo_id,
        "valor": {
            "etapas": [
                {
                    "etapa": "percepcao",
                    "sucesso": True,
                    "estado": {
                        "corpo": {
                            "cpu": {
                                "uso_percentual": cpu,
                                "estado": "normal",
                            },
                            "memoria": {
                                "uso_percentual": 40.0,
                                "estado": "normal",
                                "usado_gb": 4.0,
                                "total_gb": 16.0,
                            },
                            "armazenamento": {},
                            "processos": 120,
                        }
                    },
                }
            ],
            "necessidade_prioritaria": {
                "selecionada": {
                    "necessidade": "estabilidade",
                    "prioridade": "alta",
                }
            },
            "decisao": {
                "acao": "registrar_estado_corpo",
                "motivo": "persistir o estado observado",
            },
            "acao": {
                "sucesso": True,
                "acao": "registrar_estado_corpo",
            },
            "resultado": {
                "estado": "resultado_observado",
                "sucesso": True,
            },
            "aprendizado": {
                "texto": aprendizado,
                "estado": "observado",
            },
            "aprendizado_anterior": {
                "disponivel": True,
            },
            "delta": {
                "delta_id": f"Δ-{ciclo_id}",
                "estado_anterior": "ciclo_concluido",
                "estado_novo": "ciclo_concluido",
                "causa": "ciclo_runtime_concluido",
            },
        },
    }


def habitat(cpu_processos: float = 70.0):
    return {
        "sucesso": True,
        "estado": "habitat_observado",
        "recursos": {
            "processos_habitat": {
                "entidades": [
                    {
                        "pid": 10,
                        "nome": "processo-a",
                        "estado": "R",
                        "uso_cpu_percentual": cpu_processos,
                        "memoria_rss_mb": 100.0,
                    },
                    {
                        "pid": 11,
                        "nome": "processo-b",
                        "estado": "S",
                        "uso_cpu_percentual": 50.0,
                        "memoria_rss_mb": 80.0,
                    },
                ]
            }
        },
    }


def novo(tmp: str, clock: CicloFakeClock) -> ColetorDatasetDualAE5:
    return ColetorDatasetDualAE5(
        repositorio=Path(tmp) / "repo",
        agora=clock.agora_fn,
    )


def ler_jsonl(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    return [
        json.loads(linha)
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]


def testar_primeira_transicao_e_segunda() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = CicloFakeClock()
        coletor = novo(tmp, clock)

        primeiro = coletor.processar_ciclo(
            ciclo=ciclo("c1"),
            habitat=habitat(),
            ae4_resultado={"estado": "ae4_ciclo_observado"},
        )
        assert primeiro["coletado"] is False

        segundo = coletor.processar_ciclo(
            ciclo=ciclo("c2", cpu=30.0, aprendizado="manter observação"),
            habitat=habitat(75.0),
            ae4_resultado={"estado": "ae4_melhoria_comprovada"},
        )
        assert segundo["qwen"]["gravado"] is True
        assert segundo["kernel"]["gravado"] is True

        base = Path(tmp) / "Nyxal-datasets"
        qwen = ler_jsonl(base / "qwen-dataset.jsonl")
        kernel = ler_jsonl(base / "kernel-dataset.jsonl")
        assert len(qwen) == 1
        assert len(kernel) == 1

        assert qwen[0]["schema"] == "nyxal-qwen-transition-1"
        assert "estado_anterior" in qwen[0]["prompt"]
        assert "aprendizado" in qwen[0]["completion"]
        assert qwen[0]["causalidade_comprovada"] is False

        assert kernel[0]["schema"] == "nyxal-kernel-transition-1"
        assert kernel[0]["input"]["top5_processos"][0]["nome"] == "processo-a"
        assert kernel[0]["output_observado"]["delta_id"] == "Δ-c2"
        assert kernel[0]["output_observado"]["acao_ciclo"] == "registrar_estado_corpo"
        assert kernel[0]["treinamento_autorizado"] is False


def testar_deduplicacao_24h() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = CicloFakeClock()
        coletor = novo(tmp, clock)
        coletor.processar_ciclo(ciclo=ciclo("c1"), habitat=habitat())
        primeiro = coletor.processar_ciclo(ciclo=ciclo("c2", cpu=30.0), habitat=habitat())
        segundo = coletor.processar_ciclo(ciclo=ciclo("c3", cpu=30.0), habitat=habitat())
        assert primeiro["qwen"]["gravado"] is True
        assert primeiro["kernel"]["gravado"] is True
        assert segundo["qwen"]["deduplicado"] is True
        assert segundo["kernel"]["deduplicado"] is True


def testar_causalidade_nao_inventada() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = CicloFakeClock()
        coletor = novo(tmp, clock)
        coletor.processar_ciclo(ciclo=ciclo("c1"), habitat=habitat())
        resultado = coletor.processar_ciclo(ciclo=ciclo("c2"), habitat=habitat())
        assert resultado["qwen"]["gravado"] is True
        qwen = ler_jsonl(
            Path(tmp) / "Nyxal-datasets" / "qwen-dataset.jsonl"
        )[0]
        kernel = ler_jsonl(
            Path(tmp) / "Nyxal-datasets" / "kernel-dataset.jsonl"
        )[0]
        assert qwen["causalidade_comprovada"] is False
        assert kernel["treinamento_autorizado"] is False


def testar_atomicidade_cursor_e_invariantes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = CicloFakeClock()
        coletor = novo(tmp, clock)
        coletor.processar_ciclo(ciclo=ciclo("c1"), habitat=habitat())
        coletor.processar_ciclo(ciclo=ciclo("c2"), habitat=habitat())
        base = Path(tmp) / "Nyxal-datasets"
        estado = json.loads((base / "dual-cursor.json").read_text(encoding="utf-8"))
        indice = json.loads((base / "dual-index.json").read_text(encoding="utf-8"))
        assert estado["qwen_anterior"]["ciclo_id"] == "c2"
        assert estado["kernel_anterior"]["ciclo_id"] == "c2"
        assert indice["contagens"]["qwen"] == 1
        assert indice["contagens"]["kernel"] == 1
        assert not list(base.glob("*.tmp"))

        contexto = coletor.contexto()
        assert contexto["treinamento_automatico"] is False
        assert contexto["implantacao_automatica"] is False
        for chave in (
            "autorizacao_explicita",
            "integracao_executada",
            "stable_modificada",
            "arquitetura_modificada",
            "conhecimento_permanente",
        ):
            assert contexto["invariantes"][chave] is False


def testar_desabilitado() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = CicloFakeClock()
        coletor = ColetorDatasetDualAE5(
            repositorio=Path(tmp) / "repo",
            habilitada=False,
            agora=clock.agora_fn,
        )
        resultado = coletor.processar_ciclo(ciclo=ciclo("c1"), habitat=habitat())
        assert resultado["estado"] == "coletor_dual_ae5_desabilitado"
        assert resultado["coletado"] is False
        assert not list((Path(tmp) / "Nyxal-datasets").glob("*.jsonl"))


def testar_fonte_sem_execucao_externa() -> None:
    origem = Path("nixal_coletor_dataset_dual_ae5.py").read_text(
        encoding="utf-8"
    )
    assert "subprocess" not in origem
    assert "Popen" not in origem
    assert "os.system" not in origem
    assert "shell=True" not in origem
    assert "git merge" not in origem


def main() -> None:
    testar_primeira_transicao_e_segunda()
    testar_deduplicacao_24h()
    testar_causalidade_nao_inventada()
    testar_atomicidade_cursor_e_invariantes()
    testar_desabilitado()
    testar_fonte_sem_execucao_externa()
    print("TESTE_AE5_COLETOR_DUAL_OK")


if __name__ == "__main__":
    main()
