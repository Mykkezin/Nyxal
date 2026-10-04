#!/usr/bin/env python3
"""Teste determinístico da solicitação formal de evolução."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_solicitacao_evolucao import SolicitacaoEvolucaoNixal


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="nyxal-solicitacao-evolucao-"
    ) as diretorio:
        raiz = Path(diretorio)
        modulo = SolicitacaoEvolucaoNixal(
            repositorio=raiz / "repo",
            solicitacoes=raiz / "solicitacoes",
        )

        ciclo = {
            "estado_atual": "provisoria",
            "hipotese": (
                "A nova estratégia pode reduzir a latência."
            ),
            "necessidade": "reduzir_latencia",
            "pergunta": (
                "Como reduzir a latência do componente?"
            ),
            "tipo": "explicacao_candidata",
            "razao": "Hipótese derivada das evidências.",
            "evidencias_de_suporte": [
                {"id": "e1", "fonte": "benchmark"}
            ],
            "evidencias_contrarias_conhecidas": [],
            "contrarias_avaliadas": False,
            "confianca": "indeterminada",
            "confirmada": False,
            "testada": False,
        }

        aguardando = modulo.criar(
            ciclo_hipotese=ciclo,
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
            observacao="Ainda sem artefato.",
        )

        assert aguardando["estado"] == "aguardando_artefato"
        assert aguardando["artefato_origem"] is None
        assert aguardando["execucao_solicitada"] is False
        assert aguardando["execucao_local"] is False
        assert aguardando["autorizacao_explicita"] is False
        assert aguardando["stable_modificada"] is False

        artefato = raiz / "melhoria.py"
        artefato.write_text(
            "print('EXPERIMENTO')\n",
            encoding="utf-8",
        )

        pronta = modulo.anexar_artefato(
            aguardando["solicitacao_id"],
            artefato,
            observacao="Artefato preparado.",
        )

        assert pronta["estado"] == "pronta_para_experimento"
        assert pronta["artefato_origem"] == str(
            artefato.resolve()
        )
        assert pronta["execucao_solicitada"] is True
        assert pronta["execucao_local"] is False
        assert pronta["autorizacao_explicita"] is False
        assert pronta["integracao_executada"] is False
        assert pronta["stable_modificada"] is False

        consultada = modulo.consultar(
            aguardando["solicitacao_id"]
        )
        assert consultada["estado"] == "pronta_para_experimento"
        assert consultada["artefato_origem"] == str(
            artefato.resolve()
        )
        assert consultada["estado_anterior"] == (
            "aguardando_artefato"
        )
        assert len(consultada["historico_estados"]) == 2

        try:
            modulo.anexar_artefato(
                aguardando["solicitacao_id"],
                artefato,
            )
        except ValueError as erro:
            assert "transicao_estado_nao_permitida" in str(erro)
        else:
            raise AssertionError(
                "solicitação pronta aceitou transição repetida"
            )

        modulo_sem_artefato = SolicitacaoEvolucaoNixal(
            repositorio=raiz / "repo2",
            solicitacoes=raiz / "solicitacoes2",
        )
        sem_artefato = modulo_sem_artefato.criar(
            ciclo_hipotese=ciclo,
            objetivo="objetivo",
            metrica="tempo",
            direcao_melhor="menor",
            baseline=1.0,
        )
        try:
            modulo_sem_artefato.iniciar_experimento(
                sem_artefato["solicitacao_id"]
            )
        except ValueError as erro:
            assert str(erro) == (
                "artefato_experimental_nao_encontrado"
            )
        else:
            raise AssertionError(
                "solicitação sem artefato iniciou experimento"
            )

        assert modulo_sem_artefato.consultar(
            sem_artefato["solicitacao_id"]
        )["estado"] == "aguardando_artefato"

        resultado = modulo.iniciar_experimento(
            aguardando["solicitacao_id"]
        )
        assert resultado["estado"] == "experimento_em_execucao"
        assert resultado["estado_anterior"] == (
            "pronta_para_experimento"
        )

        resultado = modulo.registrar_resultado_experimento(
            resultado["solicitacao_id"],
            {
                "sucesso": True,
                "estado": "solicitacao_executada",
                "valor": {
                    "estado": "proposta_criada",
                    "experimento_id": "exp-final",
                    "comparacao": {"aprovado": True},
                },
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            },
        )
        assert resultado["estado"] == "experimento_concluido"
        assert resultado["estado_anterior"] == (
            "experimento_em_execucao"
        )

        try:
            modulo.anexar_artefato(
                resultado["solicitacao_id"],
                artefato,
            )
        except ValueError as erro:
            assert "transicao_estado_nao_permitida" in str(erro)
        else:
            raise AssertionError(
                "solicitação final aceitou nova transição"
            )

        try:
            modulo.registrar_resultado_experimento(
                resultado["solicitacao_id"],
                {
                    "sucesso": True,
                    "estado": "solicitacao_executada",
                    "valor": {
                        "estado": "proposta_criada",
                    },
                },
            )
        except ValueError as erro:
            assert str(erro) == "solicitacao_nao_em_execucao"
        else:
            raise AssertionError(
                "solicitação final aceitou novo resultado"
            )

        historico = resultado["historico_estados"]
        assert [item["para"] for item in historico] == [
            "aguardando_artefato",
            "pronta_para_experimento",
            "experimento_em_execucao",
            "experimento_concluido",
        ]

        rejeitado = dict(ciclo)
        rejeitado["estado_atual"] = "confirmada"

        try:
            modulo.criar(
                ciclo_hipotese=rejeitado,
                objetivo="x",
                metrica="tempo",
                direcao_melhor="menor",
                baseline=1,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "hipótese não provisória foi aceita"
            )

    print("=" * 64)
    print("TESTE — SOLICITAÇÃO FORMAL DE EVOLUÇÃO")
    print("=" * 64)
    print("HIPOTESE_VALIDADA=OK")
    print("SOLICITACAO_CRIADA=OK")
    print("AGUARDANDO_ARTEFATO=OK")
    print("ARTEFATO_VALIDADO=OK")
    print("MAQUINA_ESTADOS_MONOTONICA=OK")
    print("HIPOTESE_NAO_CONFIRMADA=OK")
    print("SEM_EXECUCAO_LOCAL=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("STABLE_MODIFICADA=FALSE")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
