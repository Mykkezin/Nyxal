import builtins
import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError

from nixal_agregador_operacional import agregar
from nixal_analise_operacional import (
    AnaliseOperacional,
    ResultadoAnalise,
    analisar,
    consultar_ciclo,
    consultar_par,
)
from nixal_normalizador_operacional import RelacaoOperacional


def relacao(
    origem="A",
    destino="B",
    ciclo="ciclo-1",
    instante="2026-10-07T00:00:00+00:00",
    autoridade="observacional",
    tipo="observacao",
    evidencia="evidencia",
):
    return RelacaoOperacional(
        origem=origem,
        destino=destino,
        tipo=tipo,
        evidencia=evidencia,
        proveniencia="teste",
        ciclo=ciclo,
        instante=instante,
        autoridade=autoridade,
    )


def grafo(relacoes):
    resultado = agregar(relacoes)
    assert not resultado.rejeitado
    return resultado.sucesso


class TesteAnaliseOperacional(unittest.TestCase):

    def test_01_grafo_valido_aceito(self):
        g = grafo([relacao("A", "B")])
        resultado = analisar(g)

        self.assertFalse(resultado.rejeitado)
        self.assertIsInstance(resultado.sucesso, AnaliseOperacional)

    def test_02_entrada_invalida_rejeitada(self):
        resultado = analisar(object())

        self.assertTrue(resultado.rejeitado)
        self.assertIsNone(resultado.sucesso)

    def test_03_conserva_quantidade_relacoes(self):
        relacoes = [
            relacao("A", "B", evidencia="e1"),
            relacao("B", "C", evidencia="e2"),
            relacao("C", "D", evidencia="e3"),
        ]

        analise = analisar(grafo(relacoes)).sucesso

        self.assertEqual(analise.total_relacoes, 3)
        self.assertEqual(analise.relacoes, tuple(relacoes))

    def test_04_conta_nos(self):
        g = grafo([
            relacao("A", "B"),
            relacao("B", "C"),
            relacao("A", "C"),
        ])

        analise = analisar(g).sucesso

        self.assertEqual(analise.total_nos, 3)

    def test_05_nao_deduplica(self):
        r = relacao("A", "B", evidencia="mesma")
        analise = analisar(grafo([r, r])).sucesso

        self.assertEqual(analise.total_relacoes, 2)
        self.assertEqual(analise.pares[("A", "B")], 2)

    def test_06_ciclos_distintos(self):
        r1 = relacao("A", "B", ciclo="X")
        r2 = relacao("A", "B", ciclo="Y")

        analise = analisar(grafo([r1, r2])).sucesso

        self.assertEqual(analise.total_ciclos, 2)
        self.assertEqual(analise.relacoes_por_ciclo["X"], 1)
        self.assertEqual(analise.relacoes_por_ciclo["Y"], 1)

    def test_07_none_e_string_none_distintos(self):
        r1 = relacao("A", "B", ciclo=None)
        r2 = relacao("B", "C", ciclo="None")

        analise = analisar(grafo([r1, r2])).sucesso

        self.assertEqual(analise.relacoes_por_ciclo[None], 1)
        self.assertEqual(analise.relacoes_por_ciclo["None"], 1)

    def test_08_autoridade_observacional(self):
        analise = analisar(
            grafo([
                relacao("A", "B", autoridade="observacional")
            ])
        ).sucesso

        self.assertEqual(analise.autoridades["observacional"], 1)

    def test_09_autoridade_experimental(self):
        analise = analisar(
            grafo([
                relacao("A", "B", autoridade="experimental")
            ])
        ).sucesso

        self.assertEqual(analise.autoridades["experimental"], 1)

    def test_10_nao_cria_autoridade_arquitetural(self):
        r = relacao("A", "B", autoridade="observacional")
        analise = analisar(grafo([r])).sucesso

        self.assertNotIn("arquitetural", analise.autoridades)

    def test_11_conta_tipos_sem_inventar(self):
        analise = analisar(
            grafo([
                relacao("A", "B", tipo="observacao"),
                relacao("B", "C", tipo="observacao"),
            ])
        ).sucesso

        self.assertEqual(dict(analise.tipos), {"observacao": 2})

    def test_12_nao_inferencia_transitiva(self):
        r1 = relacao("A", "B")
        r2 = relacao("B", "C")

        analise = analisar(grafo([r1, r2])).sucesso

        self.assertEqual(
            consultar_par(analise, "A", "C"),
            (),
        )
        self.assertEqual(len(analise.relacoes), 2)

    def test_13_consulta_par_exata(self):
        r1 = relacao("A", "B", evidencia="e1")
        r2 = relacao("A", "C", evidencia="e2")

        analise = analisar(grafo([r1, r2])).sucesso

        self.assertEqual(
            consultar_par(analise, "A", "B"),
            (r1,),
        )

    def test_14_consulta_ciclo_exata(self):
        r1 = relacao("A", "B", ciclo="X")
        r2 = relacao("B", "C", ciclo="Y")

        analise = analisar(grafo([r1, r2])).sucesso

        self.assertEqual(
            consultar_ciclo(analise, "X"),
            (r1,),
        )
        self.assertEqual(
            consultar_ciclo(analise, "Y"),
            (r2,),
        )

    def test_15_nos_nao_resolvidos_contra_planta(self):
        g = grafo([relacao("componente_inexistente", "outro")])
        analise = analisar(g).sucesso

        self.assertEqual(analise.total_nos, 2)

    def test_16_relacoes_originais_sao_preservadas(self):
        r = relacao("A", "B")
        g = grafo([r])
        analise = analisar(g).sucesso

        self.assertIs(analise.relacoes[0], r)

    def test_17_resultado_imutavel(self):
        analise = analisar(grafo([]))

        with self.assertRaises(FrozenInstanceError):
            analise.sucesso = None

    def test_18_colecoes_imutaveis(self):
        analise = analisar(
            grafo([relacao("A", "B")])
        ).sucesso

        with self.assertRaises(TypeError):
            analise.autoridades["novo"] = 1

    def test_19_grafo_original_nao_alterado(self):
        r = relacao("A", "B")
        g = grafo([r])

        antes = g.relacoes

        analisar(g)

        self.assertEqual(g.relacoes, antes)

    def test_20_grafo_vazio(self):
        analise = analisar(grafo([])).sucesso

        self.assertEqual(analise.total_relacoes, 0)
        self.assertEqual(analise.total_nos, 0)
        self.assertEqual(analise.total_ciclos, 0)
        self.assertEqual(analise.relacoes, ())

    def test_21_consulta_sem_resultado(self):
        analise = analisar(
            grafo([relacao("A", "B")])
        ).sucesso

        self.assertEqual(
            consultar_par(analise, "X", "Y"),
            (),
        )

    def test_22_consulta_ciclo_sem_resultado(self):
        analise = analisar(
            grafo([relacao("A", "B", ciclo="X")])
        ).sucesso

        self.assertEqual(
            consultar_ciclo(analise, "Y"),
            (),
        )

    def test_23_modulo_nao_importa_planta(self):
        modulo = importlib.import_module("nixal_analise_operacional")

        self.assertNotIn("planta_nixal", sys.modules)
        self.assertNotIn("nixal_runtime", modulo.__dict__)

    def test_24_modulo_nao_acessa_filesystem(self):
        original_open = builtins.open

        def bloquear_open(*args, **kwargs):
            raise AssertionError("O8 não deve acessar filesystem.")

        builtins.open = bloquear_open

        try:
            resultado = analisar(
                grafo([relacao("A", "B")])
            )
        finally:
            builtins.open = original_open

        self.assertFalse(resultado.rejeitado)

    def test_25_rastreabilidade_preserva_instancias(self):
        r1 = relacao("A", "B", evidencia="e1")
        r2 = relacao("A", "B", evidencia="e2")

        analise = analisar(grafo([r1, r2])).sucesso

        encontradas = consultar_par(analise, "A", "B")

        self.assertIs(encontradas[0], r1)
        self.assertIs(encontradas[1], r2)

    def test_26_contagem_de_pares(self):
        r1 = relacao("A", "B", evidencia="e1")
        r2 = relacao("A", "B", evidencia="e2")
        r3 = relacao("B", "C", evidencia="e3")

        analise = analisar(grafo([r1, r2, r3])).sucesso

        self.assertEqual(analise.pares[("A", "B")], 2)
        self.assertEqual(analise.pares[("B", "C")], 1)

    def test_27_contagem_por_autoridade(self):
        relacoes = [
            relacao("A", "B", autoridade="observacional"),
            relacao("B", "C", autoridade="observacional"),
            relacao("C", "D", autoridade="experimental"),
        ]

        analise = analisar(grafo(relacoes)).sucesso

        self.assertEqual(
            dict(analise.autoridades),
            {
                "observacional": 2,
                "experimental": 1,
            },
        )

    def test_28_contagem_por_ciclo(self):
        relacoes = [
            relacao("A", "B", ciclo="X"),
            relacao("B", "C", ciclo="X"),
            relacao("C", "D", ciclo="Y"),
        ]

        analise = analisar(grafo(relacoes)).sucesso

        self.assertEqual(
            dict(analise.relacoes_por_ciclo),
            {
                "X": 2,
                "Y": 1,
            },
        )

    def test_29_consulta_preserva_ordem(self):
        r1 = relacao("A", "B", evidencia="e1")
        r2 = relacao("A", "B", evidencia="e2")

        analise = analisar(grafo([r1, r2])).sucesso

        self.assertEqual(
            consultar_par(analise, "A", "B"),
            (r1, r2),
        )

    def test_30_analise_e_deterministica_exceto_instante_externo(self):
        relacoes = [
            relacao("A", "B", evidencia="e1"),
            relacao("B", "C", evidencia="e2"),
        ]

        a1 = analisar(grafo(relacoes)).sucesso
        a2 = analisar(grafo(relacoes)).sucesso

        self.assertEqual(a1.total_relacoes, a2.total_relacoes)
        self.assertEqual(a1.total_nos, a2.total_nos)
        self.assertEqual(a1.total_ciclos, a2.total_ciclos)
        self.assertEqual(a1.autoridades, a2.autoridades)
        self.assertEqual(a1.tipos, a2.tipos)
        self.assertEqual(a1.pares, a2.pares)


if __name__ == "__main__":
    unittest.main(verbosity=2)
