#!/usr/bin/env python3
"""Teste determinístico da política AE2 e da integração com o ciclo residente."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_auto_experimento_ae2 import AutoExperimentoIsoladoAE2
from nixal_solicitacao_evolucao import SolicitacaoEvolucaoNixal


class RuntimeFalso:
    def __init__(self, resultado=None):
        self.chamadas = []
        self.resultado = resultado or {
            "sucesso": True,
            "estado": "solicitacao_evolucao_remota_executada",
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

    def executar_solicitacao_evolucao_remota(self, solicitacao_id):
        self.chamadas.append(solicitacao_id)
        return dict(self.resultado)


def hipotese():
    return {
        "estado_atual": "provisoria",
        "hipotese": "A estratégia experimental pode reduzir a latência.",
        "necessidade": "reduzir_latencia",
        "pergunta": "Como reduzir a latência?",
        "tipo": "explicacao_candidata",
        "razao": "Evidência inicial.",
        "evidencias_de_suporte": [{"id": "e1"}],
        "evidencias_contrarias_conhecidas": [],
        "contrarias_avaliadas": False,
        "confianca": "indeterminada",
        "confirmada": False,
        "testada": False,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nyxal-ae2-") as diretorio:
        raiz = Path(diretorio)
        solicitacoes = SolicitacaoEvolucaoNixal(
            repositorio=raiz / "repo",
            solicitacoes=raiz / "solicitacoes",
        )
        runtime = RuntimeFalso()

        desabilitado = AutoExperimentoIsoladoAE2(
            runtime,
            solicitacoes,
            habilitada=False,
        )
        resultado = desabilitado.processar_pendentes()
        assert resultado["estado"] == "ae2_desabilitada"
        assert runtime.chamadas == []

        repositorio = raiz / "repo"
        repositorio.mkdir(parents=True, exist_ok=True)
        artefato = repositorio / "melhoria.py"
        artefato.write_text("print('AE2_TEST')\n", encoding="utf-8")

        criado = solicitacoes.criar(
            ciclo_hipotese=hipotese(),
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
        )
        pronto = solicitacoes.anexar_artefato(
            criado["solicitacao_id"],
            artefato,
        )

        ae2 = AutoExperimentoIsoladoAE2(
            runtime,
            solicitacoes,
            habilitada=True,
        )

        primeiro = ae2.processar_pendentes()
        assert primeiro["sucesso"] is True
        assert primeiro["estado"] == "experimento_processado"
        assert primeiro["processada"] is True
        assert primeiro["solicitacao_id"] == pronto["solicitacao_id"]
        assert runtime.chamadas == [pronto["solicitacao_id"]]
        assert primeiro["retry_automatico"] is False

        segundo = ae2.processar_pendentes()
        assert segundo["estado"] == "sem_solicitacao_pendente"
        assert runtime.chamadas == [pronto["solicitacao_id"]]

        criado_bloqueado = solicitacoes.criar(
            ciclo_hipotese=hipotese(),
            objetivo="testar bloqueio",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
        )
        pronto_bloqueado = solicitacoes.anexar_artefato(
            criado_bloqueado["solicitacao_id"],
            artefato,
        )
        caminho = Path(solicitacoes.solicitacoes) / (
            pronto_bloqueado["solicitacao_id"] + ".json"
        )
        import json
        registro = json.loads(caminho.read_text(encoding="utf-8"))
        registro["autorizacao_explicita"] = True
        caminho.write_text(
            json.dumps(registro, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        terceiro = ae2.processar_pendentes()
        assert terceiro["sucesso"] is False
        assert terceiro["estado"] == "solicitacao_bloqueada_pela_politica"
        assert terceiro["motivo"] == "autorizacao_invalida"
        assert runtime.chamadas == [pronto["solicitacao_id"]]

        contexto = ae2.contexto()
        assert contexto["execucao_experimental_automatica"] is True
        assert contexto["max_por_ciclo"] == 1
        assert contexto["autorizacao_explicita"] is False
        assert contexto["stable_modificada"] is False

    print("=" * 64)
    print("TESTE — AUTO-EXPERIMENTO AE2")
    print("=" * 64)
    print("AE2_DESABILITADA_SEM_EXECUCAO=OK")
    print("SOLICITACAO_PRONTA=OK")
    print("POLITICA_VALIDADA=OK")
    print("DELEGACAO_RUNTIME_N9=OK")
    print("MAXIMO_UM_EXPERIMENTO=OK")
    print("SEM_RETRY_AUTOMATICO=OK")
    print("BLOQUEIO_AUTORIZACAO=OK")
    print("SEM_ALTERACAO_STABLE=OK")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
