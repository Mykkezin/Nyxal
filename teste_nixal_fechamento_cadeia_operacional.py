from __future__ import annotations

import dataclasses
import importlib
import inspect
import unittest

from nixal_fechamento_cadeia_operacional import (
    FechamentoCadeiaOperacional,
    ORDEM_CADEIA,
    fechar,
)


class TesteFechamentoCadeiaOperacional(
    unittest.TestCase
):

    def setUp(self):
        self.cadeia = (
            {
                "etapa": "O9",
                "identidade": "EVID-001",
                "estado": "consolidada",
            },
            {
                "etapa": "O10",
                "identidade": "QUAL-001",
                "estado": "qualificada",
            },
            {
                "etapa": "O11",
                "identidade": "REU-001",
                "estado": "reutilizada",
            },
            {
                "etapa": "O12",
                "identidade": "COMP-001",
                "estado": "comparada",
            },
            {
                "etapa": "O13",
                "identidade": "PAT-001",
                "estado": "recorrente",
            },
            {
                "etapa": "O14",
                "identidade": "CAND-001",
                "estado": "candidato",
            },
        )

    def test_01_cadeia_valida_produz_fechamento(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertIsInstance(
            resultado,
            FechamentoCadeiaOperacional,
        )

    def test_02_entrada_ausente_rejeitada(self):
        with self.assertRaises(
            ValueError
        ):
            fechar(None)

    def test_03_cadeia_vazia_rejeitada(self):
        with self.assertRaises(
            ValueError
        ):
            fechar(())

    def test_04_o9_ausente(self):
        cadeia = self.cadeia[1:]

        with self.assertRaises(
            ValueError
        ):
            fechar(cadeia)

    def test_05_o10_ausente(self):
        cadeia = (
            self.cadeia[0],
            *self.cadeia[2:],
        )

        with self.assertRaises(
            ValueError
        ):
            fechar(cadeia)

    def test_06_o11_ausente(self):
        cadeia = (
            self.cadeia[0],
            self.cadeia[1],
            *self.cadeia[3:],
        )

        with self.assertRaises(
            ValueError
        ):
            fechar(cadeia)

    def test_07_o12_ausente(self):
        cadeia = (
            *self.cadeia[:3],
            *self.cadeia[4:],
        )

        with self.assertRaises(
            ValueError
        ):
            fechar(cadeia)

    def test_08_o13_ausente(self):
        cadeia = (
            *self.cadeia[:4],
            self.cadeia[5],
        )

        with self.assertRaises(
            ValueError
        ):
            fechar(cadeia)

    def test_09_o14_ausente(self):
        cadeia = self.cadeia[:5]

        with self.assertRaises(
            ValueError
        ):
            fechar(cadeia)

    def test_10_ordem_obrigatoria(self):
        cadeia = (
            self.cadeia[0],
            self.cadeia[1],
            self.cadeia[2],
            self.cadeia[3],
            self.cadeia[5],
            self.cadeia[4],
        )

        with self.assertRaises(
            ValueError
        ):
            fechar(cadeia)

    def test_11_preserva_o9(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertEqual(
            resultado.identidades_artefatos[0],
            "EVID-001",
        )

    def test_12_preserva_o10(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertEqual(
            resultado.identidades_artefatos[1],
            "QUAL-001",
        )

    def test_13_preserva_o11(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertEqual(
            resultado.identidades_artefatos[2],
            "REU-001",
        )

    def test_14_preserva_o12(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertEqual(
            resultado.identidades_artefatos[3],
            "COMP-001",
        )

    def test_15_preserva_o13(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertEqual(
            resultado.identidades_artefatos[4],
            "PAT-001",
        )

    def test_16_preserva_o14(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertEqual(
            resultado.identidades_artefatos[5],
            "CAND-001",
        )

    def test_17_candidato_obrigatorio(self):
        cadeia = list(
            self.cadeia
        )

        cadeia[-1] = {
            **cadeia[-1],
            "estado": "aprendido",
        }

        with self.assertRaises(
            ValueError
        ):
            fechar(tuple(cadeia))

    def test_18_aprendido_rejeitado(self):
        cadeia = list(
            self.cadeia
        )

        cadeia[-1] = {
            **cadeia[-1],
            "estado": "aprendido",
        }

        with self.assertRaises(
            ValueError
        ):
            fechar(tuple(cadeia))

    def test_19_integrado_rejeitado(self):
        cadeia = list(
            self.cadeia
        )

        cadeia[-1] = {
            **cadeia[-1],
            "estado": "candidato",
            "integrado": True,
        }

        with self.assertRaises(
            ValueError
        ):
            fechar(tuple(cadeia))

    def test_20_autorizacao_rejeitada(self):
        cadeia = list(
            self.cadeia
        )

        cadeia[-1] = {
            **cadeia[-1],
            "autorizacao_integracao": True,
        }

        with self.assertRaises(
            ValueError
        ):
            fechar(tuple(cadeia))

    def test_21_estado_fechado(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertEqual(
            resultado.estado,
            "fechado",
        )

        self.assertTrue(
            resultado.cadeia_fechada
        )

    def test_22_handoff_preparado(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertTrue(
            resultado.handoff_preparado
        )

    def test_23_handoff_nao_e_aprendizado(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertNotEqual(
            resultado.estado,
            "aprendido",
        )

        self.assertFalse(
            hasattr(
                resultado,
                "aprendizado",
            )
        )

    def test_24_handoff_nao_e_integracao(self):
        resultado = fechar(
            self.cadeia
        )

        self.assertFalse(
            hasattr(
                resultado,
                "integrado",
            )
        )

    def test_25_identidade_deterministica(self):
        a = fechar(
            self.cadeia
        )

        b = fechar(
            self.cadeia
        )

        self.assertEqual(
            a.identidade,
            b.identidade,
        )

    def test_26_mesma_cadeia_mesmo_fechamento(self):
        a = fechar(
            self.cadeia
        )

        b = fechar(
            self.cadeia
        )

        self.assertEqual(
            a,
            b,
        )

    def test_27_fechamento_imutavel(self):
        resultado = fechar(
            self.cadeia
        )

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            resultado.estado = "aberto"

    def test_28_entrada_nao_modificada(self):
        antes = tuple(
            dict(etapa)
            for etapa in self.cadeia
        )

        fechar(
            self.cadeia
        )

        depois = tuple(
            dict(etapa)
            for etapa in self.cadeia
        )

        self.assertEqual(
            antes,
            depois,
        )

    def test_29_llc_nao_executado(self):
        modulo = importlib.import_module(
            "nixal_fechamento_cadeia_operacional"
        )

        nomes = set(
            modulo.__dict__
        )

        proibidos = {
            "nixal_aprendizado_llc",
            "nixal_fechamento_llc",
            "ReplicacaoLLC",
        }

        self.assertTrue(
            nomes.isdisjoint(proibidos)
        )

    def test_30_modulo_isolado(self):
        modulo = importlib.import_module(
            "nixal_fechamento_cadeia_operacional"
        )

        fonte = inspect.getsource(
            modulo
        )

        proibidos = (
            "open(",
            "Path(",
            "socket",
            "requests",
            "urllib",
            "subprocess",
            "os.system",
        )

        for item in proibidos:
            self.assertNotIn(
                item,
                fonte,
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
