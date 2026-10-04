#!/usr/bin/env python3
"""Contrato determinístico do Nível 10.

Este teste valida o contrato documental do ciclo local antes da implementação
operacional. Ele intentionally não executa código de candidato, não altera
branches e não depende de rede.
"""

from __future__ import annotations

from pathlib import Path


CONTRATO = Path(__file__).with_name("NIVEL_10_CONTRATO.md")


REQUIRED = [
    "## 1. Objetivo",
    "## 3. Escopo",
    "## 4. Máquina de estados",
    "## 5. Identidade do ciclo",
    "## 6. Detecção",
    "## 7. Sincronização",
    "## 8. Validação",
    "## 9. Critério de aprovação",
    "## 10. Persistência e auditoria",
    "## 11. Relação com o Nível 9",
    "## 12. Invariantes obrigatórias",
    "## 13. Critérios de aceite do contrato",
]


def main() -> None:
    assert CONTRATO.is_file(), "contrato_nivel10_ausente"
    conteudo = CONTRATO.read_text(encoding="utf-8")

    for marcador in REQUIRED:
        assert marcador in conteudo, f"marcador_ausente:{marcador}"

    assert "main" in conteudo
    assert "não é modificada" in conteudo
    assert "aprovado" in conteudo
    assert "rejeitado" in conteudo
    assert "autorização" in conteudo

    print("CONTRATO_NIVEL10_PRESENTE=OK")
    print("ESCOPO_NIVEL10_FORMALIZADO=OK")
    print("INVARIANTES_NIVEL10_DECLARADAS=OK")
    print("CRITERIOS_ACEITE_NIVEL10_DECLARADOS=OK")
    print("PASSOU: True")


if __name__ == "__main__":
    main()
