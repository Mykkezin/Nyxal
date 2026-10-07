from __future__ import annotations

import dataclasses
import importlib
import inspect
import unittest
from dataclasses import dataclass

from nixal_padroes_recorrentes_operacional import (
    PadraoRecorrente,
    detectar,
)


@dataclass(frozen=True)
class RelacaoTeste:
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


class TestePadroesRecorrentesOperacional(unittest.TestCase):

    def setUp(self):
        self.r_ab_obs = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c1",
        )

        self.r_ab_obs_c2 = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c2",
        )

        self.r_bc_persist = RelacaoTeste(
            "B",
            "C",
            "persistencia",
            "observacional",
            "c1",
        )

        self.r_ac_trans = RelacaoTeste(
            "A",
            "C",
            "transformacao",
            "experimental",
            "c2",
        )

        self.e1 = EvidenciaTeste(
            "ev-001",
            "qualificada",
            (
                self.r_ab_obs,
                self.r_bc_persist,
            ),
        )

        self.e2 = EvidenciaTeste(
            "ev-002",
            "qualificada",
            (
                self.r_ab_obs_c2,
                self.r_ac_trans,
            ),
        )

    def test_01_duas_evidencias_geram_recorrencia(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        self.assertEqual(
            resultado.total_padroes,
            1,
        )

    def test_02_entrada_vazia_rejeitada(self):
        with self.assertRaises(ValueError):
            detectar(())

    def test_03_entrada_nao_iteravel_rejeitada(self):
        with self.assertRaises(ValueError):
            detectar(123)

    def test_04_nao_qualificada_rejeitada(self):
        invalida = EvidenciaTeste(
            "ev-x",
            "rejeitada",
            (self.r_ab_obs,),
        )

        with self.assertRaises(ValueError):
            detectar((self.e1, invalida))

    def test_05_identidade_ausente_rejeitada(self):
        @dataclass(frozen=True)
        class SemIdentidade:
            estado: str
            relacoes: tuple

        evidencia = SemIdentidade(
            "qualificada",
            (self.r_ab_obs,),
        )

        with self.assertRaises(ValueError):
            detectar((evidencia,))

    def test_06_relacoes_ausentes_rejeitada(self):
        @dataclass(frozen=True)
        class SemRelacoes:
            identidade: str
            estado: str

        evidencia = SemRelacoes(
            "ev-x",
            "qualificada",
        )

        with self.assertRaises(ValueError):
            detectar((evidencia,))

    def test_07_origem_ausente_rejeitada(self):
        @dataclass(frozen=True)
        class RelacaoSemOrigem:
            destino: str
            tipo: str
            autoridade: str
            ciclo: str

        evidencia = EvidenciaTeste(
            "ev-x",
            "qualificada",
            (
                RelacaoSemOrigem(
                    "B",
                    "observacao",
                    "observacional",
                    "c1",
                ),
            ),
        )

        with self.assertRaises(ValueError):
            detectar((evidencia, evidencia))

    def test_08_destino_ausente_rejeitada(self):
        @dataclass(frozen=True)
        class RelacaoSemDestino:
            origem: str
            tipo: str
            autoridade: str
            ciclo: str

        evidencia = EvidenciaTeste(
            "ev-x",
            "qualificada",
            (
                RelacaoSemDestino(
                    "A",
                    "observacao",
                    "observacional",
                    "c1",
                ),
            ),
        )

        with self.assertRaises(ValueError):
            detectar((evidencia, evidencia))

    def test_09_tipo_ausente_rejeitada(self):
        @dataclass(frozen=True)
        class RelacaoSemTipo:
            origem: str
            destino: str
            autoridade: str
            ciclo: str

        evidencia = EvidenciaTeste(
            "ev-x",
            "qualificada",
            (
                RelacaoSemTipo(
                    "A",
                    "B",
                    "observacional",
                    "c1",
                ),
            ),
        )

        with self.assertRaises(ValueError):
            detectar((evidencia, evidencia))

    def test_10_autoridade_ausente_rejeitada(self):
        @dataclass(frozen=True)
        class RelacaoSemAutoridade:
            origem: str
            destino: str
            tipo: str
            ciclo: str

        evidencia = EvidenciaTeste(
            "ev-x",
            "qualificada",
            (
                RelacaoSemAutoridade(
                    "A",
                    "B",
                    "observacao",
                    "c1",
                ),
            ),
        )

        with self.assertRaises(ValueError):
            detectar((evidencia, evidencia))

    def test_11_mesmo_padrao_em_duas_evidencias(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        padrao = resultado.padroes[0]

        self.assertEqual(
            padrao.frequencia_evidencias,
            2,
        )

    def test_12_repeticao_na_mesma_evidencia_nao_e_independencia(self):
        evidencia = EvidenciaTeste(
            "ev-001",
            "qualificada",
            (
                self.r_ab_obs,
                self.r_ab_obs,
            ),
        )

        outro = EvidenciaTeste(
            "ev-002",
            "qualificada",
            (self.r_ab_obs,),
        )

        resultado = detectar(
            (evidencia, outro)
        )

        padrao = resultado.padroes[0]

        self.assertEqual(
            padrao.frequencia_evidencias,
            2,
        )

    def test_13_frequencia_conta_evidencias_distintas(self):
        e3 = EvidenciaTeste(
            "ev-003",
            "qualificada",
            (self.r_ab_obs,),
        )

        resultado = detectar(
            (self.e1, self.e2, e3)
        )

        padrao = resultado.padroes[0]

        self.assertEqual(
            padrao.frequencia_evidencias,
            3,
        )

    def test_14_identidade_da_evidencia_preservada(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        padrao = resultado.padroes[0]

        self.assertEqual(
            padrao.evidencias_distintas,
            ("ev-001", "ev-002"),
        )

    def test_15_ciclo_preservado(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        padrao = resultado.padroes[0]

        self.assertEqual(
            padrao.ciclos_observados,
            ("c1", "c2"),
        )

    def test_16_relacao_original_preservada(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        padrao = resultado.padroes[0]

        self.assertIs(
            padrao.ocorrencias[0].relacao,
            self.r_ab_obs,
        )

    def test_17_nao_recorrente_nao_retorna(self):
        resultado = detectar(
            (self.e1,)
        )

        self.assertEqual(
            resultado.total_padroes,
            0,
        )

    def test_18_padroes_distintos_separados(self):
        e3 = EvidenciaTeste(
            "ev-003",
            "qualificada",
            (self.r_ac_trans,),
        )

        e4 = EvidenciaTeste(
            "ev-004",
            "qualificada",
            (self.r_ac_trans,),
        )

        resultado = detectar(
            (self.e1, self.e2, e3, e4)
        )

        self.assertEqual(
            resultado.total_padroes,
            2,
        )

    def test_19_tipos_diferentes_sao_padroes_diferentes(self):
        a = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c1",
        )

        b = RelacaoTeste(
            "A",
            "B",
            "persistencia",
            "observacional",
            "c1",
        )

        ea = EvidenciaTeste("ea", "qualificada", (a,))
        eb = EvidenciaTeste("eb", "qualificada", (b,))

        resultado = detectar((ea, eb))

        self.assertEqual(
            resultado.total_padroes,
            0,
        )

    def test_20_autoridades_diferentes_sao_padroes_diferentes(self):
        a = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c1",
        )

        b = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "experimental",
            "c1",
        )

        ea = EvidenciaTeste("ea", "qualificada", (a,))
        eb = EvidenciaTeste("eb", "qualificada", (b,))

        resultado = detectar((ea, eb))

        self.assertEqual(
            resultado.total_padroes,
            0,
        )

    def test_21_ciclos_diferentes_compartilham_padrao(self):
        e2 = EvidenciaTeste(
            "ev-002",
            "qualificada",
            (self.r_ab_obs_c2,),
        )

        resultado = detectar(
            (self.e1, e2)
        )

        self.assertEqual(
            resultado.total_padroes,
            1,
        )

    def test_22_origem_diferente(self):
        a = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c1",
        )

        b = RelacaoTeste(
            "X",
            "B",
            "observacao",
            "observacional",
            "c1",
        )

        ea = EvidenciaTeste("ea", "qualificada", (a,))
        eb = EvidenciaTeste("eb", "qualificada", (b,))

        resultado = detectar((ea, eb))

        self.assertEqual(
            resultado.total_padroes,
            0,
        )

    def test_23_destino_diferente(self):
        a = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c1",
        )

        b = RelacaoTeste(
            "A",
            "X",
            "observacao",
            "observacional",
            "c1",
        )

        ea = EvidenciaTeste("ea", "qualificada", (a,))
        eb = EvidenciaTeste("eb", "qualificada", (b,))

        resultado = detectar((ea, eb))

        self.assertEqual(
            resultado.total_padroes,
            0,
        )

    def test_24_resultado_imutavel(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            resultado.total_padroes = 999

    def test_25_evidencias_imutaveis(self):
        antes_1 = dataclasses.asdict(self.e1)
        antes_2 = dataclasses.asdict(self.e2)

        detectar((self.e1, self.e2))

        self.assertEqual(
            antes_1,
            dataclasses.asdict(self.e1),
        )

        self.assertEqual(
            antes_2,
            dataclasses.asdict(self.e2),
        )

    def test_26_relacoes_nao_modificadas(self):
        antes = self.e1.relacoes

        detectar((self.e1, self.e2))

        self.assertEqual(
            antes,
            self.e1.relacoes,
        )

    def test_27_nao_cria_causalidade(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        self.assertFalse(
            hasattr(resultado, "causalidade")
        )

        self.assertNotIn(
            "causalidade",
            repr(resultado).lower(),
        )

    def test_28_nao_cria_aprendizado(self):
        resultado = detectar(
            (self.e1, self.e2)
        )

        self.assertFalse(
            hasattr(resultado, "aprendizado")
        )

    def test_29_determinismo(self):
        a = detectar(
            (self.e1, self.e2)
        )

        b = detectar(
            (self.e1, self.e2)
        )

        self.assertEqual(a, b)

    def test_30_modulo_isolado(self):
        modulo = importlib.import_module(
            "nixal_padroes_recorrentes_operacional"
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

        fonte = inspect.getsource(modulo)

        proibidos_fonte = (
            "open(",
            "Path(",
            "socket",
            "requests",
            "urllib",
            "subprocess",
            "os.system",
        )

        for item in proibidos_fonte:
            self.assertNotIn(item, fonte)


if __name__ == "__main__":
    unittest.main(verbosity=2)
