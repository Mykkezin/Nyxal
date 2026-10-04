#!/usr/bin/env python3
"""Prova mínima do habitat persistente do Nível 10."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nyxos_habitat import NyxOSHabitat


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "nyxos"
        habitat = NyxOSHabitat(raiz)
        estado = habitat.inicializar()

        esperados = {
            "runtime", "memory", "knowledge", "body", "tools", "projects",
            "experiments", "processes", "events", "interface", "delta", "logs",
        }
        assert all((raiz / nome).is_dir() for nome in esperados)
        assert estado["estado"] == "ativo"

        processo = habitat.registrar_processo("runtime")
        assert processo["processo_id"] in habitat.estado()["processos_ativos"]

        evento = habitat.registrar_evento("ciclo_iniciado", {"ciclo": "nivel10-01"})
        assert evento["evento_id"].startswith("EV-")

        delta = habitat.registrar_delta(
            tipo="habitat",
            estado_anterior="inicial",
            estado_novo="ativo",
            causa="inicializacao_nivel_10",
            ciclo="nivel10-01",
            resultado="ok",
            evidencias=[evento["evento_id"]],
        )
        assert delta["delta_id"].startswith("Δ-")
        assert habitat.estado()["ultimo_delta"] == delta["delta_id"]

        # Reabrir o habitat em um novo objeto prova persistência em disco.
        reaberto = NyxOSHabitat(raiz)
        estado_reaberto = reaberto.inicializar()
        assert estado_reaberto["estado"] == "ativo"
        assert delta["delta_id"] == estado_reaberto["ultimo_delta"]

        eventos = (raiz / "events" / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
        deltas = (raiz / "delta" / "delta.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(eventos) == 2
        assert len(deltas) == 1
        json.loads(eventos[0])
        json.loads(eventos[1])
        json.loads(deltas[0])

        print("TESTE_NYXOS_HABITAT_OK")
        print("PERSISTENCIA=OK")
        print("PROCESSOS=OK")
        print("EVENTOS=OK")
        print("DELTA=OK")
        print("REABERTURA=OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
