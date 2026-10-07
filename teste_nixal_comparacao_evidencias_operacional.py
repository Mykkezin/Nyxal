from __future__ import annotations

import dataclasses
import importlib
import inspect
import unittest
from dataclasses import dataclass

from nixal_comparacao_evidencias_operacional import (
    ComparacaoEvidencias,
    comparar,
)


@dataclass(frozen=True)
class RelacaoTeste:
    identidade: str
    origem: str
    destino: str
    tipo: str
    autoridade: str
    ciclo: str | None


@dataclass(frozen=True)
class EvidenciaTeste:
    identidade: str
    estado: str
    relacoes: tuple[RelacaoTeste, ...]


class TesteComparacaoEvidenciasOperacional(unittest.TestCase):

    def setUp(self):
        self.r1 = RelacaoTeste(
            "r1", "A", "B", "observacao", "observacional", "c1"
        )
        self.r2 = RelacaoTeste(
            "r2", "B", "C", "persistencia", "observacional", "c1"
        )
        self.r3 = RelacaoTeste(
            "r3", "A", "C", "transformacao", "experimental", "c2"
        )
        self.r4 = RelacaoTeste(
            "r4", "C", "D", "observacao", "observacional", "c2"
        )

        self.a = EvidenciaTeste(
            "ev-A",
            "qualificada",
            (self.r1, self.r2, self.r3),
        )

        self.b = EvidenciaTeste(
            "ev-B",
            "qualificada",
            (self.r2, self.r3, self.r4),
        )

    def test_01_duas_evidencias_qualificadas_comparaveis(self):
        resultado = comparar(self.a, self.b)
        self.assertIsInstance(resultado, ComparacaoEvidencias)

    def test_02_entrada_invalida_rejeitada(self):
        with self.assertRaises(ValueError):
            comparar(object(), self.b)

    def test_03_nao_qualificada_rejeitada(self):
        invalida = EvidenciaTeste(
            "ev-X",
            "rejeitada",
            (self.r1,),
        )
        with self.assertRaises(ValueError):
            comparar(invalida, self.b)

    def test_04_identidades_preservadas(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(resultado.identidade_primeira, "ev-A")
        self.assertEqual(resultado.identidade_segunda, "ev-B")

    def test_05_evidencias_iguais(self):
        resultado = comparar(self.a, self.a)
        self.assertTrue(resultado.iguais)
        self.assertTrue(resultado.sobreposicao)

    def test_06_intersecao(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(
            resultado.intersecao,
            (self.r2, self.r3),
        )

    def test_07_exclusivas_primeira(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(
            resultado.exclusivas_primeira,
            (self.r1,),
        )

    def test_08_exclusivas_segunda(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(
            resultado.exclusivas_segunda,
            (self.r4,),
        )

    def test_09_cardinalidade_primeira(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(resultado.total_primeira, 3)

    def test_10_cardinalidade_segunda(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(resultado.total_segunda, 3)

    def test_11_cardinalidade_intersecao(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(resultado.total_intersecao, 2)

    def test_12_cardinalidade_exclusivas(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(resultado.total_exclusivas_primeira, 1)
        self.assertEqual(resultado.total_exclusivas_segunda, 1)

    def test_13_relacoes_originais_preservadas(self):
        resultado = comparar(self.a, self.b)
        self.assertIs(resultado.intersecao[0], self.r2)
        self.assertIs(resultado.exclusivas_primeira[0], self.r1)
        self.assertIs(resultado.exclusivas_segunda[0], self.r4)

    def test_14_duplicatas_legitimas_nao_removidas(self):
        evidencia = EvidenciaTeste(
            "ev-D",
            "qualificada",
            (self.r1, self.r1),
        )

        resultado = comparar(evidencia, self.a)

        self.assertEqual(
            resultado.total_primeira,
            2,
        )

        self.assertEqual(
            resultado.intersecao,
            (self.r1, self.r1),
        )

    def test_15_ordem_preservada(self):
        resultado = comparar(self.a, self.b)
        self.assertEqual(
            resultado.relacoes_primeira,
            (self.r1, self.r2, self.r3),
        )
        self.assertEqual(
            resultado.relacoes_segunda,
            (self.r2, self.r3, self.r4),
        )

    def test_16_intersecao_simetrica(self):
        ab = comparar(self.a, self.b)
        ba = comparar(self.b, self.a)

        self.assertEqual(
            set(ab.intersecao),
            set(ba.intersecao),
        )

    def test_17_exclusivas_respeitam_ordem(self):
        ab = comparar(self.a, self.b)
        ba = comparar(self.b, self.a)

        self.assertEqual(
            ab.exclusivas_primeira,
            ba.exclusivas_segunda,
        )

        self.assertEqual(
            ab.exclusivas_segunda,
            ba.exclusivas_primeira,
        )

    def test_18_nao_cria_relacoes(self):
        resultado = comparar(self.a, self.b)

        todas = (
            resultado.intersecao
            + resultado.exclusivas_primeira
            + resultado.exclusivas_segunda
        )

        self.assertTrue(
            set(todas).issubset(
                set(self.a.relacoes + self.b.relacoes)
            )
        )

    def test_19_nao_cria_causalidade(self):
        resultado = comparar(self.a, self.b)
        texto = repr(resultado).lower()
        self.assertNotIn("causalidade", texto)

    def test_20_nao_cria_transitividade(self):
        resultado = comparar(self.a, self.b)

        ids = {
            relacao.identidade
            for relacao in (
                resultado.intersecao
                + resultado.exclusivas_primeira
                + resultado.exclusivas_segunda
            )
        }

        self.assertEqual(
            ids,
            {"r1", "r2", "r3", "r4"},
        )

    def test_21_nao_aumenta_autoridade(self):
        resultado = comparar(self.a, self.b)

        autoridades = {
            relacao.autoridade
            for relacao in (
                resultado.intersecao
                + resultado.exclusivas_primeira
                + resultado.exclusivas_segunda
            )
        }

        self.assertEqual(
            autoridades,
            {"observacional", "experimental"},
        )

    def test_22_nao_produz_aprendizado(self):
        resultado = comparar(self.a, self.b)
        self.assertFalse(
            hasattr(resultado, "aprendizado")
        )

    def test_23_resultado_imutavel(self):
        resultado = comparar(self.a, self.b)

        with self.assertRaises(dataclasses.FrozenInstanceError):
            resultado.iguais = False

    def test_24_evidencias_imutaveis(self):
        antes_a = dataclasses.asdict(self.a)
        antes_b = dataclasses.asdict(self.b)

        comparar(self.a, self.b)

        self.assertEqual(
            antes_a,
            dataclasses.asdict(self.a),
        )

        self.assertEqual(
            antes_b,
            dataclasses.asdict(self.b),
        )

    def test_25_determinismo(self):
        a = comparar(self.a, self.b)
        b = comparar(self.a, self.b)

        self.assertEqual(a, b)

    def test_26_ciclos_diferentes(self):
        x = RelacaoTeste(
            "rx",
            "X",
            "Y",
            "observacao",
            "observacional",
            "c10",
        )

        y = RelacaoTeste(
            "ry",
            "X",
            "Y",
            "observacao",
            "observacional",
            "c20",
        )

        ea = EvidenciaTeste(
            "ea",
            "qualificada",
            (x,),
        )

        eb = EvidenciaTeste(
            "eb",
            "qualificada",
            (y,),
        )

        resultado = comparar(ea, eb)

        self.assertFalse(resultado.iguais)
        self.assertFalse(resultado.sobreposicao)

    def test_27_tipos_diferentes(self):
        x = RelacaoTeste(
            "rx",
            "X",
            "Y",
            "observacao",
            "observacional",
            "c1",
        )

        y = RelacaoTeste(
            "ry",
            "X",
            "Y",
            "persistencia",
            "observacional",
            "c1",
        )

        ea = EvidenciaTeste("ea", "qualificada", (x,))
        eb = EvidenciaTeste("eb", "qualificada", (y,))

        resultado = comparar(ea, eb)

        self.assertEqual(
            resultado.total_primeira,
            1,
        )
        self.assertEqual(
            resultado.total_segunda,
            1,
        )

    def test_28_autoridades_diferentes(self):
        x = RelacaoTeste(
            "rx",
            "X",
            "Y",
            "observacao",
            "observacional",
            "c1",
        )

        y = RelacaoTeste(
            "ry",
            "X",
            "Y",
            "observacao",
            "experimental",
            "c1",
        )

        ea = EvidenciaTeste("ea", "qualificada", (x,))
        eb = EvidenciaTeste("eb", "qualificada", (y,))

        resultado = comparar(ea, eb)

        self.assertFalse(resultado.iguais)

    def test_29_modulo_nao_importa_runtime_planta(self):
        modulo = importlib.import_module(
            "nixal_comparacao_evidencias_operacional"
        )

        nomes = set(modulo.__dict__)

        proibidos = {
            "nixal_runtime",
            "nixal_ciclo_residente",
            "nixal_autorreprentacao",
            "leitor_planta",
        }

        self.assertTrue(
            nomes.isdisjoint(proibidos)
        )

    def test_30_modulo_nao_acessa_filesystem_rede(self):
        modulo = importlib.import_module(
            "nixal_comparacao_evidencias_operacional"
        )

        fonte = inspect.getsource(modulo)

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
            self.assertNotIn(item, fonte)


if __name__ == "__main__":
    unittest.main(verbosity=2)
