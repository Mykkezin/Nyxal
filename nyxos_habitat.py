#!/usr/bin/env python3
"""NyxOS — habitat persistente experimental.

Nível 10: cria a estrutura persistente onde Runtime, memória, processos,
eventos, interface e Delta podem operar juntos. Não cria kernel próprio.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


class NyxOSHabitat:
    SUBSISTEMAS = (
        "runtime", "memory", "knowledge", "body", "tools", "projects",
        "experiments", "processes", "events", "interface", "delta", "logs",
    )

    def __init__(self, raiz: str | Path = "nyxos") -> None:
        self.raiz = Path(raiz)

    @staticmethod
    def _agora() -> str:
        return datetime.now(timezone.utc).isoformat()

    def inicializar(self) -> dict:
        self.raiz.mkdir(parents=True, exist_ok=True)
        criados = []
        for nome in self.SUBSISTEMAS:
            caminho = self.raiz / nome
            caminho.mkdir(parents=True, exist_ok=True)
            criados.append(nome)

        estado = self.raiz / "estado.json"
        if not estado.exists():
            estado.write_text(json.dumps({
                "versao_habitat": 1,
                "estado": "ativo",
                "criado_em": self._agora(),
                "atualizado_em": self._agora(),
                "processos_ativos": [],
                "ultimo_delta": None,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self._garantir_log(self.raiz / "events" / "eventos.jsonl")
        self._garantir_log(self.raiz / "delta" / "delta.jsonl")
        return self.estado()

    def _garantir_log(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.touch(exist_ok=True)

    def registrar_evento(self, tipo: str, dados: dict | None = None) -> dict:
        evento = {
            "evento_id": "EV-" + uuid.uuid4().hex,
            "tipo": tipo,
            "timestamp": self._agora(),
            "dados": dados or {},
        }
        with (self.raiz / "events" / "eventos.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
        return evento

    def registrar_delta(
        self,
        *,
        tipo: str,
        estado_anterior: str,
        estado_novo: str,
        causa: str,
        ciclo: str | None = None,
        resultado: str | None = None,
        evidencias: list | None = None,
    ) -> dict:
        delta = {
            "delta_id": "Δ-" + uuid.uuid4().hex,
            "tipo": tipo,
            "estado_anterior": estado_anterior,
            "estado_novo": estado_novo,
            "causa": causa,
            "evidencias": evidencias or [],
            "ciclo": ciclo,
            "resultado": resultado,
            "timestamp": self._agora(),
        }
        with (self.raiz / "delta" / "delta.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(delta, ensure_ascii=False) + "\n")

        estado = self._ler_estado()
        estado["atualizado_em"] = self._agora()
        estado["ultimo_delta"] = delta["delta_id"]
        self._gravar_estado(estado)
        return delta

    def registrar_processo(self, nome: str, comando: list[str] | None = None) -> dict:
        processo = {
            "processo_id": "PROC-" + uuid.uuid4().hex,
            "nome": nome,
            "comando": comando or [],
            "estado": "registrado",
            "pid": None,
            "criado_em": self._agora(),
        }
        caminho = self.raiz / "processes" / f"{processo['processo_id']}.json"
        caminho.write_text(json.dumps(processo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        estado = self._ler_estado()
        estado.setdefault("processos_ativos", []).append(processo["processo_id"])
        self._gravar_estado(estado)
        self.registrar_evento("processo_registrado", processo)
        return processo

    def estado(self) -> dict:
        return self._ler_estado()

    def _ler_estado(self) -> dict:
        caminho = self.raiz / "estado.json"
        if not caminho.exists():
            return self.inicializar()
        return json.loads(caminho.read_text(encoding="utf-8"))

    def _gravar_estado(self, estado: dict) -> None:
        (self.raiz / "estado.json").write_text(
            json.dumps(estado, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    habitat = NyxOSHabitat()
    habitat.inicializar()
    print(json.dumps(habitat.estado(), ensure_ascii=False, indent=2))
