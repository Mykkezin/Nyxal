#!/usr/bin/env python3
"""Validação M5.16 — adaptador de host controlado."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_adaptador_host_controlado import AdaptadorHostControladoNixOS


def main() -> None:
    pasta = Path(tempfile.mkdtemp(prefix="nyxos_m5_16_"))
    adaptador = AdaptadorHostControladoNixOS(
        arquivo=pasta / "adaptador.json",
    )

    observar = adaptador.executar("observar")
    assert observar["estado"] == "executado_controlado"
    assert observar["executada"] is True
    assert observar["atuacao_fisica"] is False
    assert observar["mutacao_host"] is False
    assert observar["resultado"]["pid"] > 0

    aguardar = adaptador.executar("aguardar")
    assert aguardar["executada"] is True
    assert aguardar["atuacao_fisica"] is False
    assert aguardar["mutacao_host"] is False

    preparar = adaptador.executar("preparar_gateway")
    assert preparar["executada"] is True
    assert preparar["atuacao_fisica"] is False
    assert preparar["mutacao_host"] is False

    reduzir = adaptador.executar("reduzir_carga")
    assert reduzir["estado"] == "bloqueado"
    assert reduzir["motivo"] == "atuacao_fisica_nao_implementada"
    assert reduzir["executada"] is False
    assert reduzir["mutacao_host"] is False

    preservar = adaptador.executar("preservar_estado")
    assert preservar["estado"] == "bloqueado"
    assert preservar["motivo"] == "atuacao_fisica_nao_implementada"
    assert preservar["executada"] is False

    assert (pasta / "adaptador.json").is_file()

    contexto = adaptador.contexto()
    assert contexto["atuacao_fisica_habilitada"] is False
    assert contexto["mutacao_host_habilitada"] is False
    assert contexto["modo"] == "controlado_somente_leitura"

    print("TESTE_M5_16_ADAPTADOR_HOST_CONTROLADO_OK")
    print("LEITURA_HOST: HABILITADA")
    print("MUTACAO_HOST: BLOQUEADA")
    print("ATUACAO_FISICA: NAO_IMPLEMENTADA")
    print("MODO: CONTROLADO_SOMENTE_LEITURA")


if __name__ == "__main__":
    main()
