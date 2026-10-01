#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_runtime import NyxalRuntime
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal


class PercepcaoDeterministica:
    def __call__(self, cpu_anterior=None):
        return (
            {
                "identidade": {"nome": "Nixal"},
                "corpo": {
                    "cpu": {
                        "uso_percentual": 12.0,
                        "estado": "baixa_carga",
                        "calibrada": True,
                    },
                    "memoria": {"uso_percentual": 20.0},
                    "temperaturas_gerais": [],
                    "gpu": [],
                    "armazenamento": {"uso_percentual": 50.0},
                    "processos": 1,
                    "uptime_segundos": 10.0,
                },
                "percepcao": {
                    "timestamp": "2026-10-01T00:00:00-03:00"
                },
            },
            {"cpu": [1, 2, 3]},
        )


def verificar(condicao: bool, mensagem: str) -> None:
    estado = "PASS" if condicao else "FALHA"
    print(f"[{estado}] {mensagem}")
    if not condicao:
        raise AssertionError(mensagem)


def main() -> None:
    with TemporaryDirectory() as tmp:
        base = Path(tmp)

        memoria = MemoriaInvestigacaoNixal(
            base / "memoria_investigacao.json"
        )

        runtime = NyxalRuntime(
            perceber_corpo=PercepcaoDeterministica(),
            arquivo_estado=base / "estado_runtime.json",
            arquivo_log=base / "log_runtime.json",
            memoria_investigacao=memoria,
        )

        # Contrato pretendido para a integração da investigação.
        resultado = runtime.executar_ciclo()

        verificar(
            resultado.get("sucesso") is True,
            "Runtime continua executando o ciclo base",
        )

        verificar(
            resultado.get("estado") == "ciclo_concluido",
            "Runtime continua concluindo o ciclo base",
        )

        valor = resultado.get("valor", {})

        verificar(
            valor.get("conhecimento_permanente") is False,
            "conhecimento permanente permanece falso",
        )

        verificar(
            valor.get("arquitetura_modificada") is False,
            "arquitetura permanece sem modificação",
        )

        verificar(
            memoria.quantidade() >= 1,
            "ciclo de hipótese é persistido na memória de investigação",
        )

        # A Fase 02 deverá expor explicitamente o resultado
        # da investigação quando integrada.
        verificar(
            "investigacao" in valor,
            "Runtime expõe resultado da investigação",
        )

        verificar(
            "hipotese" in valor,
            "Runtime expõe resultado da hipótese",
        )

        verificar(
            valor["investigacao"].get("estado")
            == "avaliacao_integrada_no_ciclo",
            "investigação chega até avaliação integrada no ciclo",
        )

        verificar(
            valor["hipotese"].get("estado_atual")
            == "suportada",
            "hipótese chega ao estado avaliado",
        )

        investigacao_valor = valor["investigacao"].get(
            "valor",
            {}
        )

        verificar(
            isinstance(investigacao_valor, dict)
            and "preparacao_teste" in investigacao_valor,
            "Runtime expõe preparação do teste",
        )

        verificar(
            isinstance(investigacao_valor, dict)
            and "integracao_teste" in investigacao_valor,
            "Runtime expõe integração do teste",
        )

        verificar(
            isinstance(investigacao_valor, dict)
            and "integracao_avaliacao" in investigacao_valor,
            "Runtime expõe integração da avaliação",
        )

        verificar(
            isinstance(investigacao_valor, dict)
            and "consolidacao_conhecimento" in investigacao_valor,
            "Runtime expõe resultado da consolidação",
        )

        consolidacao = investigacao_valor.get(
            "consolidacao_conhecimento",
            {},
        )

        verificar(
            isinstance(consolidacao, dict)
            and consolidacao.get("estado")
            == "candidato_conhecimento_criado",
            "gate cria candidato dentro do Runtime",
        )

        candidato = (
            consolidacao.get("valor", {})
            if isinstance(consolidacao, dict)
            else {}
        )

        verificar(
            isinstance(candidato, dict)
            and candidato.get("texto")
            == valor["hipotese"].get("hipotese"),
            "candidato preserva a hipótese no Runtime",
        )

        verificar(
            isinstance(candidato, dict)
            and candidato.get("gravado") is False,
            "candidato ainda não é gravado pelo Runtime",
        )

        verificar(
            isinstance(candidato, dict)
            and candidato.get("conhecimento_permanente") is False,
            "candidato ainda não é permanente no Runtime",
        )

        verificar(
            valor["hipotese"].get("conhecimento_permanente")
            is False,
            "hipótese não promove conhecimento permanente",
        )

        verificar(
            valor.get("arquitetura_modificada")
            is False,
            "hipótese não modifica arquitetura",
        )

        verificar(
            memoria.quantidade() >= 1,
            "ciclo de hipótese é persistido na memória de investigação",
        )

    print("=" * 60)
    print("TESTE — NYXAL RUNTIME + INVESTIGAÇÃO")
    print("=" * 60)
    print("PASSOU: True")
    print("=" * 60)


if __name__ == "__main__":
    main()
