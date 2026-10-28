#!/usr/bin/env python3
"""Teste do auditor somente leitura do Gate AE5.

`auditar()` lê `../Nyxal-evolution-discovery` em relação ao repositório e
devolve o resumo econômico da AE5. As fixtures abaixo ficam dentro de um
diretório temporário que faz de "repo" o filho desse diretório, então o
auditor nunca enxerga as descobertas reais da máquina que roda o teste.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from auditar_evidencias_ae5 import auditar


def escrever(caminho: Path, valor: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")


def linha_de_valor(caminho: Path, estado: str) -> None:
    escrever(caminho, {"estado": estado, "valor_estimado": 12})


def main() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario)
        repo = raiz / "repo"
        repo.mkdir()
        descoberta = raiz / "Nyxal-evolution-discovery"
        auditoria = descoberta / "auditoria"

        resultado_vazio = auditar(repo)
        assert resultado_vazio["gate"] == "AE5_VALOR_ECONOMICO"
        assert resultado_vazio["estado"] == "sem_evidencia_economica"
        assert resultado_vazio["somente_leitura"] is True
        assert resultado_vazio["auditorias_ae5"] == 0
        assert resultado_vazio["linhas_economicas"] == 0
        assert resultado_vazio["linhas_maduras"] == 0

        # A API também aceita o caminho de um arquivo dentro do repositório,
        # como ocorre no valor padrão do CLI.
        resultado_vazio_arquivo = auditar(repo / "auditar_evidencias_ae5.py")
        assert resultado_vazio_arquivo["estado"] == "sem_evidencia_economica"
        assert resultado_vazio_arquivo["somente_leitura"] is True

        for chave, valor in resultado_vazio["invariantes"].items():
            assert valor is False, f"invariante violada: {chave}"
        assert resultado_vazio["invariantes"] == {
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }

        escrever(
            descoberta / "valor-um.json",
            {"estado": "maduro_para_formalizacao"},
        )
        escrever(
            descoberta / "valor-dois.json",
            {"estado": "em_observacao"},
        )
        escrever(descoberta / "valor-tres.json", {"estado": "em_observacao"})
        escrever(auditoria / "ae5-um.json", {"nova_linha": True})
        escrever(auditoria / "ae5-dois.json", {"motivo": "duplicata_exata_24h"})
        escrever(auditoria / "ae5-tres.json", {"motivo": "tipo_em_cooldown"})
        escrever(
            auditoria / "ae5-quatro.json",
            {"motivo": "valor_economico_ausente_ou_incompleto"},
        )
        # JSON corrompido ou de outra forma não entra nas contagens: o auditor
        # é somente leitura e não pode quebrar por causa de um arquivo alheio.
        (descoberta / "valor-quebrado.json").write_text("{", encoding="utf-8")
        (auditoria / "ae5-quebrado.json").write_text("[1,2]", encoding="utf-8")

        resultado = auditar(repo)
        assert resultado["estado"] == "evidencia_economica_encontrada"
        assert resultado["auditorias_ae5"] == 4
        assert resultado["linhas_economicas"] == 3
        assert resultado["linhas_maduras"] == 1
        assert resultado["descobertas_novas"] == 1
        assert resultado["duplicadas_24h"] == 1
        assert resultado["cooldown"] == 1
        assert resultado["sem_valor"] == 1
        assert resultado["estados"] == {
            "maduro_para_formalizacao": 1,
            "em_observacao": 2,
        }
        assert resultado["somente_leitura"] is True
        for chave, valor in resultado["invariantes"].items():
            assert valor is False, f"invariante violada: {chave}"

        # O limite recorta a leitura mais recente; sem ele o auditor poderia
        # carregar um diretório de descobertas arbitrariamente grande. Os
        # mtimes são fixados para que "mais recente" seja uma ordem definida.
        sandbox_limite = raiz / "limite" / "repo"
        sandbox_limite.mkdir(parents=True)
        auditoria_limite = (
            raiz / "limite" / "Nyxal-evolution-discovery" / "auditoria"
        )
        for indice in range(1, 4):
            caminho = auditoria_limite / f"ae5-{indice}.json"
            escrever(caminho, {"nova_linha": True})
            os.utime(caminho, (1_700_000_000 + indice,) * 2)

        assert auditar(sandbox_limite, limite=1)["auditorias_ae5"] == 1
        assert auditar(sandbox_limite, limite=2)["auditorias_ae5"] == 2
        assert auditar(sandbox_limite, limite=3)["auditorias_ae5"] == 3
        assert auditar(sandbox_limite)["auditorias_ae5"] == 3

        for limite_invalido in (0, -1, "2", None, True):
            try:
                auditar(repo, limite=limite_invalido)
            except ValueError as erro:
                assert str(erro) == "limite_invalido"
            else:
                raise AssertionError(
                    f"limite inválido aceito: {limite_invalido!r}"
                )

        # Auditor somente leitura: nada do fixture é alterado nem apagado.
        assert sorted(p.name for p in descoberta.glob("valor-*.json")) == [
            "valor-dois.json",
            "valor-quebrado.json",
            "valor-tres.json",
            "valor-um.json",
        ]
        assert auditoria.is_dir()

    print("TESTE_AUDITOR_EVIDENCIAS_AE5_OK")


if __name__ == "__main__":
    main()
