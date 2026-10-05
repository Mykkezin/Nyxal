#!/usr/bin/env python3
"""Teste do encaixe AE2 no ciclo residente."""

from __future__ import annotations

from nixal_ciclo_residente import CicloResidenteNixOS


class RuntimeFalso:
    def __init__(self) -> None:
        self.chamadas = 0

    def executar_ciclo(self):
        self.chamadas += 1
        return {
            "sucesso": True,
            "estado": "ciclo_concluido",
            "ciclo_id": "ciclo-ae2-residente",
            "valor": {
                "necessidade_prioritaria": None,
            },
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
        }


class AE2Falso:
    FONTE = "ae2_falso"

    def __init__(self) -> None:
        self.habilitada = True
        self.chamadas = 0

    def processar_pendentes(self):
        self.chamadas += 1
        return {
            "sucesso": True,
            "estado": "sem_solicitacao_pendente",
            "processada": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


class PersistenciaFalsa:
    def __init__(self) -> None:
        self.chamadas = []

    def registrar(self, *, ciclo, estado):
        self.chamadas.append((estado, ciclo))


def main() -> int:
    runtime = RuntimeFalso()
    ae2 = AE2Falso()
    persistencia = PersistenciaFalsa()

    residente = CicloResidenteNixOS(
        runtime,
        persistencia,
        None,
        ae2,
        intervalo_segundos=0,
    )

    resultados = residente.executar(max_ciclos=1)

    assert runtime.chamadas == 1
    assert ae2.chamadas == 1
    assert len(resultados) == 1
    assert resultados[0]["auto_experimento_ae2"]["estado"] == (
        "sem_solicitacao_pendente"
    )

    contexto = residente.contexto()
    assert contexto["auto_experimento_ae2_habilitado"] is True
    assert contexto["auto_evolution_execucao_automatica"] is True
    assert contexto["autorizacao_explicita"] is False
    assert contexto["integracao_executada"] is False
    assert contexto["arquitetura_modificada"] is False

    print("=" * 64)
    print("TESTE — AE2 NO CICLO RESIDENTE")
    print("=" * 64)
    print("CICLO_RUNTIME=OK")
    print("AE2_INJETADO=OK")
    print("AE2_PROCESSADO=OK")
    print("EXECUCAO_AUTOMATICA_OBSERVAVEL=OK")
    print("SEM_AUTORIZACAO=OK")
    print("SEM_ALTERACAO_STABLE=OK")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
