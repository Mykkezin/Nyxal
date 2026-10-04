#!/usr/bin/env python3
"""Prova M4: evolução controlada até proposta, sem tocar stable."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

from nixal_evolucao_controlada import (
    EvolucaoControladaNixal,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as diretorio:
        base = Path(diretorio)
        repositorio = base / "Nyxal"
        repositorio.mkdir()

        origem = base / "melhoria.py"
        origem.write_text(
            "def melhoria():\n"
            "    return 42\n",
            encoding="utf-8",
        )

        gestor = EvolucaoControladaNixal(
            repositorio=repositorio,
            experimentos=base / "experimentos",
            candidatos=base / "candidatos",
            propostas=base / "propostas",
        )

        resultado = gestor.executar_fluxo_aprovado(
            limitacao="A métrica atual pode melhorar.",
            hipotese="Uma variante experimental terá resultado superior.",
            objetivo="Validar uma melhoria mensurável sem alterar stable.",
            metrica="pontuacao",
            direcao_melhor="maior",
            baseline=0.70,
            experimental=0.85,
            arquivo="melhoria.py",
            manifesto_conteudo=json.dumps(
                {
                    "tipo": "experimento_controlado",
                    "executar": False,
                },
                ensure_ascii=False,
            ),
            artefato_origem=origem,
        )

        assert resultado["sucesso"] is True
        assert resultado["estado"] == "proposta_criada"
        assert resultado["execucao_artefato"] is False
        assert resultado["autorizacao_explicita"] is False
        assert resultado["stable_modificada"] is False

        experimento = resultado["experimento"]

        assert experimento["estado"] == "proposta_criada"
        assert experimento["comparacao"]["aprovado"] is True
        assert math.isclose(
            experimento["comparacao"]["melhoria_absoluta"],
            0.15,
            rel_tol=0.0,
            abs_tol=1e-12,
        )

        candidato = experimento["candidato"]
        assert candidato["estado"] == "candidato"
        assert candidato["integracao_stable"] is False
        assert candidato["avaliacao"]["aprovado"] is True

        proposta = resultado["proposta"]
        assert proposta["estado"] == "aguardando_autorizacao"
        assert proposta["autorizacao_explicita"] is False
        assert proposta["integracao_executada"] is False
        assert proposta["stable_modificada"] is False

        candidato_dir = Path(
            candidato["diretorio_candidato"]
        )
        assert (candidato_dir / "melhoria.py").is_file()
        assert (
            candidato_dir / "manifesto_evolucao.json"
        ).is_file()

        estado = gestor.consultar(
            experimento["experimento_id"]
        )
        assert estado["autorizacao_explicita"] is False
        assert estado["integracao_executada"] is False
        assert estado["stable_modificada"] is False

        rejeitado = gestor.executar_fluxo_aprovado(
            limitacao="A métrica atual precisa ser comparada com rigor.",
            hipotese="Uma variante inferior não deve ser promovida.",
            objetivo="Garantir rejeição quando o experimento piora a métrica.",
            metrica="pontuacao",
            direcao_melhor="maior",
            baseline=0.70,
            experimental=0.60,
            arquivo="melhoria_rejeitada.py",
            manifesto_conteudo=json.dumps(
                {
                    "tipo": "experimento_controlado",
                    "executar": False,
                },
                ensure_ascii=False,
            ),
            artefato_origem=origem,
        )

        assert rejeitado["sucesso"] is not True
        assert rejeitado["estado"] == "rejeitado"
        assert rejeitado["comparacao"]["aprovado"] is False
        assert rejeitado["candidato"] is None
        assert rejeitado["proposta"] is None

        print("=" * 60)
        print("TESTE — NÍVEL 9 / EVOLUÇÃO CONTROLADA")
        print("=" * 60)
        print("LIMITACAO=OK")
        print("HIPOTESE=OK")
        print("BASELINE=OK")
        print("EXPERIMENTO=OK")
        print("COMPARACAO=OK")
        print("REJEICAO_DE_REGRESSAO=OK")
        print("MELHORIA_APROVADA=OK")
        print("CANDIDATO=OK")
        print("PROPOSTA=OK")
        print("EXECUCAO_ARTEFATO=FALSE")
        print("AUTORIZACAO_EXPLICITA=FALSE")
        print("STABLE_MODIFICADA=FALSE")
        print("PASSOU: True")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
