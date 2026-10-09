#!/usr/bin/env python3
"""Testes unitários da composição de presença residente e legado."""

from datetime import datetime, timezone

from nixal_estado_presenca import compor_presenca_efetiva


def verificar(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise AssertionError(mensagem)
    print(f"[PASS] {mensagem}")


def main() -> None:
    agora_epoch = 1_791_568_800.0
    agora = datetime.fromtimestamp(agora_epoch, tz=timezone.utc)
    legado_encerrado = {
        "ativa": False,
        "ultimo_ciclo": "2026-09-26T18:08:59-03:00",
        "ciclos": 15,
    }
    estado_encerrado = {"modo": "encerramento", "status": "encerrada"}

    heartbeat_atual = {
        "estado_presenca": "heartbeat",
        "ultimo_heartbeat": agora_epoch - 8,
        "encerrado_em": None,
        "residencia": {"estado_residente": "executando"},
    }
    atual = compor_presenca_efetiva(
        presenca_legada=legado_encerrado,
        estado_legado=estado_encerrado,
        presenca_maquina=heartbeat_atual,
        persistencia_operacional={
            "ultima_persistencia": "2026-10-09T17:59:50+00:00",
            "ultimo_ciclo": {"concluido_em": "2026-10-09T17:59:50+00:00"},
        },
        agora_epoch=agora_epoch,
        agora=agora,
    )
    verificar(atual["ativa"] is True, "heartbeat atual supera estado legado encerrado")
    verificar(atual["origem"] == "presenca_maquina_nyxos", "origem moderna identificada")
    verificar(atual["ciclos"] is None, "não reutiliza contador legado obsoleto")

    heartbeat_antigo = dict(heartbeat_atual, ultimo_heartbeat=agora_epoch - 120)
    antiga = compor_presenca_efetiva(
        presenca_legada=legado_encerrado,
        estado_legado=estado_encerrado,
        presenca_maquina=heartbeat_antigo,
        agora_epoch=agora_epoch,
        agora=agora,
    )
    verificar(antiga["ativa"] is False, "heartbeat vencido não mantém a Nyxal online")

    encerrada = dict(heartbeat_atual, estado_presenca="encerrado")
    finalizada = compor_presenca_efetiva(
        presenca_legada=legado_encerrado,
        estado_legado=estado_encerrado,
        presenca_maquina=encerrada,
        agora_epoch=agora_epoch,
        agora=agora,
    )
    verificar(finalizada["ativa"] is False, "presença explicitamente encerrada fica offline")

    legado_recente = {
        "ativa": True,
        "ultimo_ciclo": agora.isoformat(),
        "ciclos": 22,
    }
    fallback = compor_presenca_efetiva(
        presenca_legada=legado_recente,
        estado_legado={"modo": "presenca", "status": "ativa"},
        presenca_maquina={},
        agora_epoch=agora_epoch,
        agora=agora,
    )
    verificar(fallback["ativa"] is True, "estado legado recente segue suportado")
    verificar(fallback["origem"] == "estado_nixal.json", "origem legada identificada")

    legado_obsoleto = dict(legado_recente, ultimo_ciclo="2026-09-26T18:08:59-03:00")
    obsoleto = compor_presenca_efetiva(
        presenca_legada=legado_obsoleto,
        estado_legado={"modo": "presenca", "status": "ativa"},
        presenca_maquina={},
        agora_epoch=agora_epoch,
        agora=agora,
    )
    verificar(obsoleto["ativa"] is False, "estado legado antigo não finge atividade")

    print("TESTE_ESTADO_PRESENCA_RESIDENTE_OK")


if __name__ == "__main__":
    main()
