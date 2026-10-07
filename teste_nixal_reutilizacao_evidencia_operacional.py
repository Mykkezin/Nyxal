from __future__ import annotations

import dataclasses
import importlib
import inspect
import os
import unittest
from dataclasses import dataclass

from nixal_reutilizacao_evidencia_operacional import (
    ReutilizacaoEvidencia,
    reutilizar,
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
    relacoes: tuple[RelacaoTeste, ...]


@dataclass(frozen=True)
class QualificacaoTeste:
    identidade: str
    estado: str


class TesteReutilizacaoEvidenciaOperacional(unittest.TestCase):

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
            "r4", "A", "B", "observacao", "observacional", "c2"
        )

        self.evidencia = EvidenciaTeste(
            "ev-001",
            (self.r1, self.r2, self.r3, self.r4),
        )

        self.qualificacao = QualificacaoTeste(
            "ev-001",
            "qualificada",
        )

    def test_01_evidencia_qualificada_pode_ser_reutilizada(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertTrue(resultado.reutilizada)

    def test_02_entrada_invalida_e_rejeitada(self):
        resultado = reutilizar(
            object(),
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertFalse(resultado.reutilizada)

    def test_03_qualificacao_rejeitada_nao_pode_ser_reutilizada(self):
        qualificacao = QualificacaoTeste("ev-001", "rejeitada")
        resultado = reutilizar(
            self.evidencia,
            qualificacao,
            "tipo",
            "observacao",
        )
        self.assertFalse(resultado.reutilizada)

    def test_04_identidade_coincidente_aceita(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "identidade",
            "r1",
        )
        self.assertTrue(resultado.reutilizada)

    def test_05_identidade_divergente_rejeitada(self):
        qualificacao = QualificacaoTeste("ev-999", "qualificada")
        resultado = reutilizar(
            self.evidencia,
            qualificacao,
            "tipo",
            "observacao",
        )
        self.assertFalse(resultado.reutilizada)

    def test_06_criterio_identidade(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "identidade",
            "r2",
        )
        self.assertEqual(resultado.resultado.relacoes, (self.r2,))

    def test_07_criterio_par(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "par",
            ("A", "B"),
        )
        self.assertEqual(
            resultado.resultado.relacoes,
            (self.r1, self.r4),
        )

    def test_08_criterio_ciclo(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "ciclo",
            "c1",
        )
        self.assertEqual(
            resultado.resultado.relacoes,
            (self.r1, self.r2),
        )

    def test_09_criterio_autoridade(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "autoridade",
            "experimental",
        )
        self.assertEqual(
            resultado.resultado.relacoes,
            (self.r3,),
        )

    def test_10_criterio_tipo(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "persistencia",
        )
        self.assertEqual(
            resultado.resultado.relacoes,
            (self.r2,),
        )

    def test_11_criterio_inexistente_retorna_vazio(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "inexistente",
        )
        self.assertTrue(resultado.reutilizada)
        self.assertEqual(resultado.resultado.relacoes, ())

    def test_12_ordem_original_preservada(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "par",
            ("A", "B"),
        )
        self.assertEqual(
            resultado.resultado.relacoes,
            (self.r1, self.r4),
        )

    def test_13_duplicatas_legitimas_preservadas(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertEqual(
            resultado.resultado.relacoes,
            (self.r1, self.r4),
        )

    def test_14_relacoes_retornadas_sao_as_originais(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "identidade",
            "r1",
        )
        self.assertIs(resultado.resultado.relacoes[0], self.r1)

    def test_15_nao_cria_relacoes(self):
        antes = self.evidencia.relacoes
        reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertEqual(self.evidencia.relacoes, antes)

    def test_16_nao_cria_transitividade(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "par",
            ("A", "C"),
        )
        self.assertEqual(
            resultado.resultado.relacoes,
            (self.r3,),
        )

    def test_17_nao_cria_causalidade(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertTrue(resultado.reutilizada)
        self.assertNotIn(
            "causal",
            str(resultado).lower(),
        )

    def test_18_nao_produz_autoridade_arquitetural(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "autoridade",
            "experimental",
        )
        self.assertEqual(
            resultado.resultado.relacoes[0].autoridade,
            "experimental",
        )

    def test_19_nao_produz_aprendizado(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertNotIn(
            "aprendizado",
            resultado.motivos,
        )

    def test_20_evidencia_original_imutavel(self):
        antes = dataclasses.asdict(self.evidencia)
        reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        depois = dataclasses.asdict(self.evidencia)
        self.assertEqual(antes, depois)

    def test_21_resultado_imutavel(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        ).resultado
        with self.assertRaises(dataclasses.FrozenInstanceError):
            resultado.total_relacoes = 99

    def test_22_identidade_evidencia_preservada(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertEqual(
            resultado.resultado.identidade_evidencia,
            "ev-001",
        )

    def test_23_identidade_qualificacao_preservada(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertEqual(
            resultado.resultado.identidade_qualificacao,
            "ev-001",
        )

    def test_24_criterio_preservado(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "ciclo",
            "c2",
        )
        self.assertEqual(
            resultado.resultado.criterio,
            ("ciclo", "c2"),
        )

    def test_25_cardinalidade_correta(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertEqual(
            resultado.resultado.total_relacoes,
            2,
        )

    def test_26_resultado_vazio_e_valido(self):
        resultado = reutilizar(
            self.evidencia,
            self.qualificacao,
            "ciclo",
            "c99",
        )
        self.assertTrue(resultado.reutilizada)
        self.assertEqual(
            resultado.resultado.total_relacoes,
            0,
        )

    def test_27_none_e_string_none_sao_distintos(self):
        relacao = RelacaoTeste(
            "r-none",
            "X",
            "Y",
            "observacao",
            "observacional",
            None,
        )

        evidencia = EvidenciaTeste(
            "ev-none",
            (relacao,),
        )

        qualificacao = QualificacaoTeste(
            "ev-none",
            "qualificada",
        )

        a = reutilizar(
            evidencia,
            qualificacao,
            "ciclo",
            None,
        )

        b = reutilizar(
            evidencia,
            qualificacao,
            "ciclo",
            "None",
        )

        self.assertEqual(a.resultado.relacoes, (relacao,))
        self.assertEqual(b.resultado.relacoes, ())

    def test_28_reexecucao_deterministica(self):
        a = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        b = reutilizar(
            self.evidencia,
            self.qualificacao,
            "tipo",
            "observacao",
        )
        self.assertEqual(a, b)

    def test_29_modulo_nao_importa_planta_runtime(self):
        modulo = importlib.import_module(
            "nixal_reutilizacao_evidencia_operacional"
        )
        nomes = set(modulo.__dict__)
        proibidos = {
            "nixal_runtime",
            "nixal_ciclo_residente",
            "nixal_autorreprentacao",
            "nixal_leitor_planta",
        }
        self.assertTrue(nomes.isdisjoint(proibidos))

    def test_30_modulo_nao_acessa_filesystem_rede(self):
        modulo = importlib.import_module(
            "nixal_reutilizacao_evidencia_operacional"
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
