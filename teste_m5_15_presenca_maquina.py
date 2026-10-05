#!/usr/bin/env python3
"""Validação M5.15 — presença persistente e retomada segura."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_presenca_maquina import PresencaMaquinaNixOS


def main() -> None:
    pasta = Path(
        tempfile.mkdtemp(prefix="nyxal_m5_15_")
    )
    systemd = pasta / "systemd"
    systemd.mkdir()

    for nome in (
        "nyxos.target",
        "nyxal-api.service",
        "nyxos-residente.service",
    ):
        (systemd / nome).write_text(
            "# teste\n",
            encoding="utf-8",
        )

    arquivo = pasta / "presenca.json"

    primeira = PresencaMaquinaNixOS(
        arquivo=arquivo,
        diretorio_systemd=systemd,
    )

    inicial = primeira.iniciar(timestamp=1000.0)
    assert inicial["estado_presenca"] == "ativo"
    assert inicial["retomada"]["detectada"] is False
    assert inicial["retomada"]["tipo"] == "primeira_inicializacao"
    assert all(
        inicial["residencia"]["unidades"][nome] is True
        for nome in (
            "nyxos.target",
            "nyxal-api.service",
            "nyxos-residente.service",
        )
    )

    batida = primeira.heartbeat(
        timestamp=1005.0,
        estado_residente="executando",
    )
    assert batida["estado_presenca"] == "heartbeat"
    assert batida["ultimo_heartbeat"] == 1005.0

    encerrada = primeira.encerrar(
        motivo="reinicio_controlado",
        timestamp=1010.0,
    )
    assert encerrada["estado_presenca"] == "encerrado"
    assert encerrada["motivo_encerramento"] == "reinicio_controlado"

    segunda = PresencaMaquinaNixOS(
        arquivo=arquivo,
        diretorio_systemd=systemd,
    )
    retomada_primeira = segunda.iniciar(
        timestamp=2000.0
    )
    assert retomada_primeira["retomada"]["detectada"] is False
    assert (
        retomada_primeira["retomada"]["tipo"]
        == "primeira_inicializacao"
    )

    # Simula uma queda/reinício enquanto o marcador estava ativo.
    segunda.heartbeat(
        timestamp=2005.0,
        estado_residente="executando",
    )

    terceira = PresencaMaquinaNixOS(
        arquivo=arquivo,
        diretorio_systemd=systemd,
    )
    retomada = terceira.iniciar(
        timestamp=3000.0
    )
    assert retomada["retomada"]["detectada"] is True
    assert (
        retomada["retomada"]["tipo"]
        == "retomada_apos_reinicio"
    )

    # Integração com o ciclo residente existente.
    from nixal_ciclo_residente import CicloResidenteNixOS

    class RuntimeFalso:
        def executar_ciclo(self) -> dict:
            return {
                "sucesso": True,
                "estado": "ciclo_concluido",
                "valor": {
                    "etapas": [
                        {
                            "etapa": "percepcao",
                            "estado": {
                                "corpo": {
                                    "temperaturas_gerais": [],
                                    "gpu": [],
                                }
                            },
                        }
                    ]
                },
            }

    integracao = PresencaMaquinaNixOS(
        arquivo=pasta / "presenca_residente.json",
        diretorio_systemd=systemd,
    )
    residente = CicloResidenteNixOS(
        RuntimeFalso(),
        presenca_maquina=integracao,
        intervalo_segundos=0,
    )
    ciclos = residente.executar(max_ciclos=1)
    assert len(ciclos) == 1
    assert "presenca_maquina" in ciclos[0]
    assert (
        ciclos[0]["presenca_maquina"]["estado_presenca"]
        == "heartbeat"
    )
    assert integracao.contexto()["estado_presenca"] == "encerrado"

    # O launcher e a API conhecem a nova superfície de presença.
    launcher = Path(
        "executar_nyxos_residente.py"
    ).read_text(encoding="utf-8")
    assert "PresencaMaquinaNixOS" in launcher

    api = Path(
        "nyxal_web_api.py"
    ).read_text(encoding="utf-8")
    assert "PRESENCA_MAQUINA" in api
    assert '"presenca_maquina"' in api

    # O estado persistido é um objeto único, sem histórico ilimitado.
    dados = json.loads(
        arquivo.read_text(encoding="utf-8")
    )
    assert isinstance(dados, dict)
    assert "historico" not in dados
    assert isinstance(
        dados["residencia"]["unidades"],
        dict,
    )

    contexto = terceira.contexto()
    assert contexto["historico_limitado"] is True
    assert contexto["arquivo_unico"] is True
    assert contexto["autorizacao_explicita"] is False
    assert contexto["integracao_executada"] is False
    assert contexto["arquitetura_modificada"] is False
    assert contexto["conhecimento_permanente"] is False

    codigo = Path(
        "nixal_presenca_maquina.py"
    ).read_text(encoding="utf-8")
    assert "subprocess" not in codigo
    assert "os.system" not in codigo
    assert "shell=True" not in codigo
    assert "eval(" not in codigo
    assert "exec(" not in codigo

    print("TESTE_M5_15_PRESENCA_MAQUINA_OK")
    print("MARCADOR_PERSISTENTE: OK")
    print("RETOMADA_SEGURA: OK")
    print("UNIDADES_SYSTEMD: OBSERVADAS")
    print("HISTORICO_ILIMITADO: DESABILITADO")
    print("EXECUCAO_ARBITRARIA: DESABILITADA")
    print("GOVERNANCA: PRESERVADA")


if __name__ == "__main__":
    main()
