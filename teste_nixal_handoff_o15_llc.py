from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from nixal_fechamento_cadeia_operacional import (
    FechamentoCadeiaOperacional,
    ORDEM_CADEIA,
)
from nixal_handoff_o15_llc import (
    HandoffO15LLC,
    preparar,
)


def fechamento_valido() -> FechamentoCadeiaOperacional:
    identidades = tuple(
        f"{etapa}-artifact"
        for etapa in ORDEM_CADEIA
    )
    return FechamentoCadeiaOperacional(
        identidade="CHAIN-abc123",
        estado="fechado",
        etapas=ORDEM_CADEIA,
        identidades_artefatos=identidades,
        identidade_candidato="O14-candidato",
        cadeia_fechada=True,
        handoff_preparado=True,
    )


def test_handoff_valido() -> None:
    resultado = preparar(fechamento_valido())

    assert isinstance(resultado, HandoffO15LLC)
    assert resultado.estado == "preparado"
    assert resultado.destino == "llc"
    assert resultado.identidade_fechamento == "CHAIN-abc123"
    assert resultado.identidade_candidato == "O14-candidato"


def test_handoff_nao_aprende() -> None:
    resultado = preparar(fechamento_valido())

    assert resultado.aprendizado_executado is False
    assert resultado.autorizacao_integracao is False
    assert resultado.integracao_executada is False


def test_handoff_preserva_cadeia() -> None:
    fechamento = fechamento_valido()
    resultado = preparar(fechamento)

    assert resultado.etapas == ORDEM_CADEIA
    assert resultado.identidades_artefatos == fechamento.identidades_artefatos


def test_handoff_nao_modifica_entrada() -> None:
    fechamento = fechamento_valido()
    original = fechamento

    preparar(fechamento)

    assert fechamento == original


def test_handoff_deterministico() -> None:
    primeiro = preparar(fechamento_valido())
    segundo = preparar(fechamento_valido())

    assert primeiro == segundo
    assert primeiro.identidade == segundo.identidade


def test_fechamento_invalido() -> None:
    try:
        preparar({"estado": "fechado"})  # type: ignore[arg-type]
    except ValueError as erro:
        assert str(erro) == "fechamento_o15_invalido"
    else:
        raise AssertionError("fechamento inválido foi aceito")


def test_estado_nao_fechado() -> None:
    fechamento = fechamento_valido()
    invalido = FechamentoCadeiaOperacional(
        **{
            **fechamento.__dict__,
            "estado": "aberto",
        }
    )

    try:
        preparar(invalido)
    except ValueError as erro:
        assert str(erro) == "fechamento_o15_nao_fechado"
    else:
        raise AssertionError("estado aberto foi aceito")


def test_cadeia_nao_fechada() -> None:
    fechamento = fechamento_valido()
    invalido = FechamentoCadeiaOperacional(
        **{
            **fechamento.__dict__,
            "cadeia_fechada": False,
        }
    )

    try:
        preparar(invalido)
    except ValueError as erro:
        assert str(erro) == "cadeia_o15_nao_fechada"
    else:
        raise AssertionError("cadeia não fechada foi aceita")


def test_handoff_nao_preparado() -> None:
    fechamento = fechamento_valido()
    invalido = FechamentoCadeiaOperacional(
        **{
            **fechamento.__dict__,
            "handoff_preparado": False,
        }
    )

    try:
        preparar(invalido)
    except ValueError as erro:
        assert str(erro) == "handoff_o15_nao_preparado"
    else:
        raise AssertionError("handoff não preparado foi aceito")


def test_cadeia_invalida() -> None:
    fechamento = fechamento_valido()
    invalido = FechamentoCadeiaOperacional(
        **{
            **fechamento.__dict__,
            "etapas": ("O9", "O10"),
        }
    )

    try:
        preparar(invalido)
    except ValueError as erro:
        assert str(erro) == "cadeia_o15_invalida"
    else:
        raise AssertionError("cadeia inválida foi aceita")


def test_identidade_deterministica_muda_com_entrada() -> None:
    primeiro = preparar(fechamento_valido())
    outro = FechamentoCadeiaOperacional(
        **{
            **fechamento_valido().__dict__,
            "identidade_candidato": "O14-outro",
        }
    )

    segundo = preparar(outro)

    assert primeiro.identidade != segundo.identidade


def test_handoff_imutavel() -> None:
    resultado = preparar(fechamento_valido())

    try:
        resultado.estado = "aprendido"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("handoff aceitou mutação")


if __name__ == "__main__":
    pytest.main([__file__])
