import builtins
import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError, replace

from nixal_agregador_operacional import agregar
from nixal_analise_operacional import analisar
from nixal_evidencia_operacional import consolidar
from nixal_normalizador_operacional import RelacaoOperacional
from nixal_qualificacao_evidencia_operacional import (
    QualificacaoEvidencia,
    ResultadoQualificacao,
    qualificar,
)


def relacao(
    origem="A",
    destino="B",
    ciclo="X",
    instante="2026-10-07T00:00:00+00:00",
    autoridade="observacional",
    tipo="observacao",
    evidencia="e1",
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


def evidencia(relacoes):
    grafo = agregar(relacoes)
    assert not grafo.rejeitado

    analise = analisar(grafo.sucesso)
    assert not analise.rejeitado

    resultado = consolidar(analise.sucesso)
    assert not resultado.rejeitado

    return resultado.sucesso


class TesteQualificacaoEvidenciaOperacional(unittest.TestCase):

    def test_01_evidencia_valida_qualificada(self):
        resultado = qualificar(
            evidencia([relacao("A", "B")])
        )

        self.assertFalse(resultado.rejeitado)
        self.assertEqual(
            resultado.sucesso.estado,
            "qualificada",
        )

    def test_02_entrada_invalida_rejeitada(self):
        resultado = qualificar(object())

        self.assertTrue(resultado.rejeitado)
        self.assertIsInstance(
            resultado,
            ResultadoQualificacao,
        )

    def test_03_identidade_valida(self):
        e = evidencia([relacao("A", "B")])
        resultado = qualificar(e)

        self.assertEqual(
            resultado.sucesso.identidade,
            e.identidade,
        )

    def test_04_identidade_alterada_rejeitada(self):
        e = evidencia([relacao("A", "B")])

        alterada = replace(
            e,
            identidade="EVID-identidade-falsa",
        )

        resultado = qualificar(alterada)

        self.assertEqual(
            resultado.sucesso.estado,
            "rejeitada",
        )
        self.assertIn(
            "identidade_inconsistente",
            resultado.sucesso.motivos,
        )

    def test_05_total_relacoes_valido(self):
        e = evidencia([
            relacao("A", "B"),
            relacao("B", "C"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "total_relacoes_inconsistente",
            resultado.sucesso.motivos,
        )

    def test_06_total_relacoes_invalido(self):
        e = evidencia([relacao("A", "B")])

        alterada = replace(
            e,
            total_relacoes=99,
        )

        resultado = qualificar(alterada)

        self.assertIn(
            "total_relacoes_inconsistente",
            resultado.sucesso.motivos,
        )

    def test_07_total_nos_valido(self):
        e = evidencia([
            relacao("A", "B"),
            relacao("B", "C"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "total_nos_inconsistente",
            resultado.sucesso.motivos,
        )

    def test_08_total_nos_invalido(self):
        e = evidencia([relacao("A", "B")])

        alterada = replace(
            e,
            total_nos=99,
        )

        resultado = qualificar(alterada)

        self.assertIn(
            "total_nos_inconsistente",
            resultado.sucesso.motivos,
        )

    def test_09_total_ciclos_valido(self):
        e = evidencia([
            relacao("A", "B", ciclo="X"),
            relacao("B", "C", ciclo="Y"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "total_ciclos_inconsistente",
            resultado.sucesso.motivos,
        )

    def test_10_total_ciclos_invalido(self):
        e = evidencia([
            relacao("A", "B", ciclo="X"),
        ])

        alterada = replace(
            e,
            total_ciclos=99,
        )

        resultado = qualificar(alterada)

        self.assertIn(
            "total_ciclos_inconsistente",
            resultado.sucesso.motivos,
        )

    def test_11_autoridades_validas(self):
        e = evidencia([
            relacao(
                "A",
                "B",
                autoridade="observacional",
            ),
            relacao(
                "B",
                "C",
                autoridade="experimental",
            ),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "autoridades_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_12_autoridades_inconsistentes(self):
        e = evidencia([
            relacao("A", "B"),
        ])

        alterada = replace(
            e,
            autoridades={"observacional": 99},
        )

        resultado = qualificar(alterada)

        self.assertIn(
            "autoridades_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_13_tipos_validos(self):
        e = evidencia([
            relacao("A", "B", tipo="observacao"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "tipos_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_14_tipos_inconsistentes(self):
        e = evidencia([
            relacao("A", "B", tipo="observacao"),
        ])

        alterada = replace(
            e,
            tipos={"observacao": 99},
        )

        resultado = qualificar(alterada)

        self.assertIn(
            "tipos_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_15_ciclos_validos(self):
        e = evidencia([
            relacao("A", "B", ciclo="X"),
            relacao("B", "C", ciclo="Y"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "ciclos_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_16_ciclos_inconsistentes(self):
        e = evidencia([
            relacao("A", "B", ciclo="X"),
        ])

        alterada = replace(
            e,
            relacoes_por_ciclo={"Y": 1},
        )

        resultado = qualificar(alterada)

        self.assertIn(
            "ciclos_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_17_pares_validos(self):
        e = evidencia([
            relacao("A", "B"),
            relacao("B", "C"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "pares_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_18_pares_inconsistentes(self):
        e = evidencia([
            relacao("A", "B"),
        ])

        alterada = replace(
            e,
            pares={("A", "C"): 1},
        )

        resultado = qualificar(alterada)

        self.assertIn(
            "pares_inconsistentes",
            resultado.sucesso.motivos,
        )

    def test_19_rastreabilidade_preservada(self):
        r1 = relacao("A", "B")
        r2 = relacao("B", "C")

        e = evidencia([r1, r2])

        resultado = qualificar(e)

        self.assertEqual(
            resultado.sucesso.relacoes_verificadas,
            2,
        )
        self.assertIs(e.relacoes[0], r1)
        self.assertIs(e.relacoes[1], r2)

    def test_20_duplicatas_legitimas(self):
        r = relacao("A", "B")

        e = evidencia([r, r])

        resultado = qualificar(e)

        self.assertEqual(
            resultado.sucesso.estado,
            "qualificada",
        )

    def test_21_nao_cria_relacao_transitiva(self):
        e = evidencia([
            relacao("A", "B"),
            relacao("B", "C"),
        ])

        self.assertNotIn(
            ("A", "C"),
            e.pares,
        )

    def test_22_repeticao_nao_vira_causalidade(self):
        e = evidencia([
            relacao("A", "B", evidencia="e1"),
            relacao("A", "B", evidencia="e2"),
            relacao("A", "B", evidencia="e3"),
        ])

        resultado = qualificar(e)

        self.assertEqual(
            resultado.sucesso.estado,
            "qualificada",
        )

    def test_23_nao_produz_autoridade_arquitetural(self):
        e = evidencia([
            relacao("A", "B"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "arquitetural",
            resultado.sucesso.evidencias_epistemicas,
        )

    def test_24_nao_produz_aprendizado(self):
        e = evidencia([
            relacao("A", "B"),
        ])

        resultado = qualificar(e)

        self.assertNotIn(
            "aprendizado",
            resultado.sucesso.motivos,
        )

    def test_25_evidencia_original_imutavel(self):
        e = evidencia([
            relacao("A", "B"),
        ])

        with self.assertRaises(FrozenInstanceError):
            e.total_relacoes = 99

    def test_26_resultado_imutavel(self):
        e = evidencia([
            relacao("A", "B"),
        ])

        resultado = qualificar(e)

        with self.assertRaises(FrozenInstanceError):
            resultado.sucesso = None

    def test_27_estrutura_epistemica_imutavel(self):
        e = evidencia([
            relacao(
                "A",
                "B",
                autoridade="observacional",
            )
        ])

        resultado = qualificar(e)

        with self.assertRaises(TypeError):
            resultado.sucesso.evidencias_epistemicas[
                "experimental"
            ] = 1

    def test_28_none_e_string_none(self):
        e = evidencia([
            relacao("A", "B", ciclo=None),
            relacao("B", "C", ciclo="None"),
        ])

        resultado = qualificar(e)

        self.assertEqual(
            resultado.sucesso.estado,
            "qualificada",
        )

    def test_29_modulo_nao_importa_planta_runtime(self):
        modulo = importlib.import_module(
            "nixal_qualificacao_evidencia_operacional"
        )

        self.assertNotIn(
            "planta_nixal",
            sys.modules,
        )
        self.assertNotIn(
            "nixal_runtime",
            modulo.__dict__,
        )

    def test_31_qualificacao_preserva_relacoes_para_comparacao(self):
        e = evidencia([
            relacao("A", "B"),
            relacao("B", "C"),
        ])

        resultado = qualificar(e)

        self.assertEqual(
            resultado.sucesso.relacoes,
            e.relacoes,
        )
        self.assertIs(
            resultado.sucesso.relacoes[0],
            e.relacoes[0],
        )

    def test_30_modulo_nao_acessa_filesystem(self):
        e = evidencia([
            relacao("A", "B"),
        ])

        original_open = builtins.open

        def bloquear_open(*args, **kwargs):
            raise AssertionError(
                "O10 não deve acessar filesystem."
            )

        builtins.open = bloquear_open

        try:
            resultado = qualificar(e)
        finally:
            builtins.open = original_open

        self.assertEqual(
            resultado.sucesso.estado,
            "qualificada",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
