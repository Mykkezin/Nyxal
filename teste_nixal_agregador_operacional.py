import builtins
import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError

from nixal_agregador_operacional import (
    GrafoOperacional,
    RejeicaoAgregacao,
    ResultadoAgregacao,
    agregar,
)
from nixal_normalizador_operacional import (
    RelacaoOperacional,
)


def relacao(
    origem="A",
    destino="B",
    ciclo="ciclo-1",
    instante="2026-10-07T00:00:00+00:00",
    autoridade="observacional",
    evidencia="evidencia",
    proveniencia="teste",
):
    return RelacaoOperacional(
        origem=origem,
        destino=destino,
        tipo="observacao",
        evidencia=evidencia,
        proveniencia=proveniencia,
        ciclo=ciclo,
        instante=instante,
        autoridade=autoridade,
    )


class TesteAgregadorOperacional(unittest.TestCase):

    def test_01_cinco_relacoes_preservadas(self):
        relacoes = [
            relacao("A", "B", evidencia="e1"),
            relacao("B", "C", evidencia="e2"),
            relacao("C", "D", evidencia="e3"),
            relacao("D", "E", evidencia="e4"),
            relacao("E", "F", evidencia="e5"),
        ]

        resultado = agregar(relacoes)

        self.assertFalse(resultado.rejeitado)
        self.assertIsInstance(resultado.sucesso, GrafoOperacional)
        self.assertEqual(len(resultado.sucesso.relacoes), 5)

    def test_02_elemento_nao_validado_rejeitado(self):
        relacoes = [
            relacao("A", "B"),
            {"origem": "B", "destino": "C"},
        ]

        resultado = agregar(relacoes)

        self.assertTrue(resultado.rejeitado)
        self.assertIsInstance(resultado.rejeicao, RejeicaoAgregacao)
        self.assertEqual(resultado.rejeicao.indice_falha, 1)

    def test_03_entrada_nao_lista_rejeitada(self):
        resultado = agregar(
            (
                relacao("A", "B"),
            )
        )

        self.assertTrue(resultado.rejeitado)
        self.assertEqual(
            resultado.rejeicao.regra_violada,
            "O7.1 - Entrada Exclusiva",
        )

    def test_04_lista_vazia_produz_grafo_vazio(self):
        resultado = agregar([])

        self.assertFalse(resultado.rejeitado)
        self.assertEqual(resultado.sucesso.relacoes, ())
        self.assertEqual(resultado.sucesso.nos, ())
        self.assertEqual(dict(resultado.sucesso.ciclos), {})
        self.assertEqual(resultado.sucesso.metadados["total_relacoes"], 0)
        self.assertEqual(resultado.sucesso.metadados["total_nos"], 0)
        self.assertEqual(resultado.sucesso.metadados["total_ciclos"], 0)

    def test_05_relacoes_identicas_nao_sao_deduplicadas(self):
        r = relacao("A", "B", evidencia="mesma")

        resultado = agregar([r, r])

        self.assertFalse(resultado.rejeitado)
        self.assertEqual(len(resultado.sucesso.relacoes), 2)
        self.assertIs(resultado.sucesso.relacoes[0], r)
        self.assertIs(resultado.sucesso.relacoes[1], r)

    def test_06_mesma_origem_destino_em_ciclos_diferentes(self):
        r1 = relacao("A", "B", ciclo="X", evidencia="e1")
        r2 = relacao("A", "B", ciclo="Y", evidencia="e2")

        resultado = agregar([r1, r2])

        self.assertEqual(len(resultado.sucesso.relacoes), 2)
        self.assertEqual(
            resultado.sucesso.ciclos["X"],
            (r1,),
        )
        self.assertEqual(
            resultado.sucesso.ciclos["Y"],
            (r2,),
        )

    def test_07_ciclo_none_fica_em_bucket_none(self):
        r = relacao("A", "B", ciclo=None)

        resultado = agregar([r])

        self.assertIn(None, resultado.sucesso.ciclos)
        self.assertEqual(resultado.sucesso.ciclos[None], (r,))

    def test_08_ciclo_none_nao_colide_com_string_none(self):
        r1 = relacao("A", "B", ciclo=None, evidencia="e1")
        r2 = relacao("B", "C", ciclo="None", evidencia="e2")

        resultado = agregar([r1, r2])

        self.assertIn(None, resultado.sucesso.ciclos)
        self.assertIn("None", resultado.sucesso.ciclos)
        self.assertNotEqual(
            resultado.sucesso.ciclos[None],
            resultado.sucesso.ciclos["None"],
        )

    def test_09_nao_inferencia_transitiva(self):
        r1 = relacao("A", "B")
        r2 = relacao("B", "C")

        resultado = agregar([r1, r2])

        relacoes = resultado.sucesso.relacoes

        self.assertEqual(len(relacoes), 2)
        self.assertFalse(
            any(
                r.origem == "A" and r.destino == "C"
                for r in relacoes
            )
        )

    def test_10_nos_unicos(self):
        relacoes = [
            relacao("A", "B"),
            relacao("B", "C"),
            relacao("A", "C"),
        ]

        resultado = agregar(relacoes)

        self.assertEqual(
            resultado.sucesso.nos,
            ("A", "B", "C"),
        )

    def test_11_ordem_dos_nos_preserva_primeira_aparicao(self):
        relacoes = [
            relacao("C", "D"),
            relacao("A", "B"),
            relacao("D", "A"),
        ]

        resultado = agregar(relacoes)

        self.assertEqual(
            resultado.sucesso.nos,
            ("C", "D", "A", "B"),
        )

    def test_12_ordem_das_relacoes_preservada(self):
        r1 = relacao("A", "B", evidencia="e1")
        r2 = relacao("B", "C", evidencia="e2")
        r3 = relacao("C", "D", evidencia="e3")

        resultado = agregar([r1, r2, r3])

        self.assertEqual(
            resultado.sucesso.relacoes,
            (r1, r2, r3),
        )

    def test_13_autoridade_observacional_preservada(self):
        r = relacao("A", "B", autoridade="observacional")

        resultado = agregar([r])

        self.assertEqual(
            resultado.sucesso.relacoes[0].autoridade,
            "observacional",
        )

    def test_14_autoridade_experimental_preservada(self):
        r = relacao("A", "B", autoridade="experimental")

        resultado = agregar([r])

        self.assertEqual(
            resultado.sucesso.relacoes[0].autoridade,
            "experimental",
        )

    def test_15_autoridade_arquitetural_nao_pode_entrar(self):
        r = relacao(
            "A",
            "B",
            autoridade="arquitetural",
        )

        resultado = agregar([r])

        self.assertTrue(resultado.rejeitado)
        self.assertIsNone(resultado.sucesso)
        self.assertEqual(
            resultado.rejeicao.regra_violada,
            "O7-I2 - Conservação Epistemológica",
        )
        self.assertEqual(resultado.rejeicao.indice_falha, 0)

    def test_16_relacoes_sao_imutaveis(self):
        r = relacao("A", "B")
        resultado = agregar([r])

        with self.assertRaises((FrozenInstanceError, AttributeError)):
            resultado.sucesso.relacoes[0].origem = "X"

    def test_17_ciclos_sao_imutaveis(self):
        r = relacao("A", "B")
        resultado = agregar([r])

        with self.assertRaises(TypeError):
            resultado.sucesso.ciclos["novo"] = (r,)

    def test_18_metadados_sao_imutaveis(self):
        resultado = agregar([])

        with self.assertRaises(TypeError):
            resultado.sucesso.metadados["total_relacoes"] = 999

    def test_19_resultado_e_imutavel(self):
        resultado = agregar([])

        with self.assertRaises(FrozenInstanceError):
            resultado.sucesso = None

    def test_20_fail_fast_rejeita_lista_inteira(self):
        r1 = relacao("A", "B")
        r3 = relacao("C", "D")

        resultado = agregar([
            r1,
            object(),
            r3,
        ])

        self.assertTrue(resultado.rejeitado)
        self.assertIsNone(resultado.sucesso)
        self.assertEqual(resultado.rejeicao.indice_falha, 1)

    def test_21_conservacao_epistemologica(self):
        r1 = relacao(
            "A",
            "B",
            autoridade="observacional",
            evidencia="observacao",
        )
        r2 = relacao(
            "B",
            "C",
            autoridade="experimental",
            evidencia="experimento",
        )

        resultado = agregar([r1, r2])

        self.assertEqual(
            resultado.sucesso.relacoes[0].autoridade,
            "observacional",
        )
        self.assertEqual(
            resultado.sucesso.relacoes[1].autoridade,
            "experimental",
        )

    def test_22_modulo_nao_importa_planta(self):
        modulo = importlib.import_module("nixal_agregador_operacional")

        self.assertNotIn("planta_nixal", sys.modules)
        self.assertNotIn(
            "nixal_runtime",
            modulo.__dict__,
        )

    def test_23_modulo_nao_importa_runtime(self):
        modulo = importlib.import_module("nixal_agregador_operacional")

        self.assertNotIn(
            "nixal_runtime",
            modulo.__dict__,
        )

    def test_24_agregacao_nao_acessa_filesystem(self):
        r = relacao("A", "B")

        original_open = builtins.open

        def bloquear_open(*args, **kwargs):
            raise AssertionError(
                "O7 não deve acessar o filesystem."
            )

        builtins.open = bloquear_open

        try:
            resultado = agregar([r])
        finally:
            builtins.open = original_open

        self.assertFalse(resultado.rejeitado)
        self.assertEqual(len(resultado.sucesso.relacoes), 1)

    def test_25_cardinalidade_conservada(self):
        relacoes = [
            relacao(
                "A",
                "B",
                ciclo="X",
                evidencia=f"e{i}",
                instante=f"2026-10-07T00:00:0{i}+00:00",
            )
            for i in range(5)
        ]

        resultado = agregar(relacoes)

        self.assertEqual(
            len(resultado.sucesso.relacoes),
            len(relacoes),
        )
        self.assertEqual(
            resultado.sucesso.metadados["total_relacoes"],
            5,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
