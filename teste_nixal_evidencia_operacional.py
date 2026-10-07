import builtins
import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError

from nixal_agregador_operacional import agregar
from nixal_analise_operacional import analisar
from nixal_evidencia_operacional import (
    EvidenciaOperacional,
    ResultadoEvidencia,
    consolidar,
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


def analise(relacoes):
    resultado = agregar(relacoes)
    assert not resultado.rejeitado

    resultado_analise = analisar(resultado.sucesso)
    assert not resultado_analise.rejeitado

    return resultado_analise.sucesso


class TesteEvidenciaOperacional(unittest.TestCase):

    def test_01_analise_valida_aceita(self):
        resultado = consolidar(
            analise([relacao("A", "B")])
        )

        self.assertFalse(resultado.rejeitado)
        self.assertIsInstance(
            resultado.sucesso,
            EvidenciaOperacional,
        )

    def test_02_entrada_invalida_rejeitada(self):
        resultado = consolidar(object())

        self.assertTrue(resultado.rejeitado)
        self.assertIsNone(resultado.sucesso)

    def test_03_total_relacoes_preservado(self):
        relacoes = [
            relacao("A", "B", evidencia="e1"),
            relacao("B", "C", evidencia="e2"),
            relacao("C", "D", evidencia="e3"),
        ]

        evidencia = consolidar(analise(relacoes)).sucesso

        self.assertEqual(evidencia.total_relacoes, 3)

    def test_04_total_nos_preservado(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B"),
                relacao("B", "C"),
            ])
        ).sucesso

        self.assertEqual(evidencia.total_nos, 3)

    def test_05_total_ciclos_preservado(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B", ciclo="X"),
                relacao("B", "C", ciclo="Y"),
            ])
        ).sucesso

        self.assertEqual(evidencia.total_ciclos, 2)

    def test_06_autoridade_preservada(self):
        evidencia = consolidar(
            analise([
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
        ).sucesso

        self.assertEqual(
            dict(evidencia.autoridades),
            {
                "observacional": 1,
                "experimental": 1,
            },
        )

    def test_07_tipos_preservados(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B", tipo="observacao"),
                relacao("B", "C", tipo="observacao"),
            ])
        ).sucesso

        self.assertEqual(
            dict(evidencia.tipos),
            {"observacao": 2},
        )

    def test_08_ciclos_preservados(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B", ciclo="X"),
                relacao("B", "C", ciclo="X"),
                relacao("C", "D", ciclo="Y"),
            ])
        ).sucesso

        self.assertEqual(
            dict(evidencia.relacoes_por_ciclo),
            {
                "X": 2,
                "Y": 1,
            },
        )

    def test_09_pares_preservados(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B"),
                relacao("A", "B", evidencia="e2"),
                relacao("B", "C"),
            ])
        ).sucesso

        self.assertEqual(
            evidencia.pares[("A", "B")],
            2,
        )
        self.assertEqual(
            evidencia.pares[("B", "C")],
            1,
        )

    def test_10_rastreabilidade_das_relacoes(self):
        r1 = relacao("A", "B", evidencia="e1")
        r2 = relacao("B", "C", evidencia="e2")

        evidencia = consolidar(
            analise([r1, r2])
        ).sucesso

        self.assertIs(evidencia.relacoes[0], r1)
        self.assertIs(evidencia.relacoes[1], r2)

    def test_11_nao_cria_relacoes(self):
        r1 = relacao("A", "B")
        r2 = relacao("B", "C")

        evidencia = consolidar(
            analise([r1, r2])
        ).sucesso

        self.assertEqual(
            evidencia.relacoes,
            (r1, r2),
        )
        self.assertNotIn(
            ("A", "C"),
            evidencia.pares,
        )

    def test_12_nao_inferencia_transitiva(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B"),
                relacao("B", "C"),
            ])
        ).sucesso

        self.assertNotIn(
            ("A", "C"),
            evidencia.pares,
        )

    def test_13_repeticao_nao_vira_causalidade(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B"),
                relacao("A", "B", evidencia="e2"),
                relacao("A", "B", evidencia="e3"),
            ])
        ).sucesso

        self.assertEqual(
            evidencia.pares[("A", "B")],
            3,
        )

    def test_14_nao_produz_autoridade_arquitetural(self):
        evidencia = consolidar(
            analise([
                relacao(
                    "A",
                    "B",
                    autoridade="observacional",
                )
            ])
        ).sucesso

        self.assertNotIn(
            "arquitetural",
            evidencia.autoridades,
        )

    def test_15_identidade_deterministica(self):
        relacoes = [
            relacao("A", "B", evidencia="e1"),
            relacao("B", "C", evidencia="e2"),
        ]

        e1 = consolidar(analise(relacoes)).sucesso
        e2 = consolidar(analise(relacoes)).sucesso

        self.assertEqual(
            e1.identidade,
            e2.identidade,
        )

    def test_16_identidade_muda_com_conteudo(self):
        e1 = consolidar(
            analise([relacao("A", "B", evidencia="e1")])
        ).sucesso

        e2 = consolidar(
            analise([relacao("A", "C", evidencia="e1")])
        ).sucesso

        self.assertNotEqual(
            e1.identidade,
            e2.identidade,
        )

    def test_17_identidade_nao_depende_do_instante_externo(self):
        r1 = relacao(
            "A",
            "B",
            instante="2026-10-07T01:00:00+00:00",
        )

        r2 = relacao(
            "A",
            "B",
            instante="2026-10-07T02:00:00+00:00",
        )

        e1 = consolidar(analise([r1])).sucesso
        e2 = consolidar(analise([r2])).sucesso

        self.assertNotEqual(
            e1.identidade,
            e2.identidade,
        )

    def test_18_evidencia_imutavel(self):
        evidencia = consolidar(
            analise([relacao("A", "B")])
        ).sucesso

        with self.assertRaises(FrozenInstanceError):
            evidencia.total_relacoes = 99

    def test_19_colecoes_imutaveis(self):
        evidencia = consolidar(
            analise([relacao("A", "B")])
        ).sucesso

        with self.assertRaises(TypeError):
            evidencia.autoridades["novo"] = 1

    def test_20_relacoes_imutaveis(self):
        evidencia = consolidar(
            analise([relacao("A", "B")])
        ).sucesso

        with self.assertRaises(
            (FrozenInstanceError, AttributeError)
        ):
            evidencia.relacoes[0].origem = "X"

    def test_21_analise_original_nao_alterada(self):
        a = analise([relacao("A", "B")])
        antes = a.relacoes

        consolidar(a)

        self.assertEqual(a.relacoes, antes)

    def test_22_analise_vazia(self):
        evidencia = consolidar(
            analise([])
        ).sucesso

        self.assertEqual(
            evidencia.total_relacoes,
            0,
        )
        self.assertEqual(
            evidencia.total_nos,
            0,
        )
        self.assertEqual(
            evidencia.total_ciclos,
            0,
        )
        self.assertEqual(
            evidencia.relacoes,
            (),
        )

    def test_23_modulo_nao_importa_planta(self):
        modulo = importlib.import_module(
            "nixal_evidencia_operacional"
        )

        self.assertNotIn(
            "planta_nixal",
            sys.modules,
        )
        self.assertNotIn(
            "nixal_runtime",
            modulo.__dict__,
        )

    def test_24_modulo_nao_acessa_filesystem(self):
        original_open = builtins.open

        def bloquear_open(*args, **kwargs):
            raise AssertionError(
                "O9 não deve acessar filesystem."
            )

        builtins.open = bloquear_open

        try:
            resultado = consolidar(
                analise([relacao("A", "B")])
            )
        finally:
            builtins.open = original_open

        self.assertFalse(resultado.rejeitado)

    def test_25_resultado_rejeitado_e_estruturado(self):
        resultado = consolidar(None)

        self.assertIsInstance(
            resultado,
            ResultadoEvidencia,
        )
        self.assertTrue(resultado.rejeitado)

    def test_26_ordem_preservada(self):
        r1 = relacao("A", "B", evidencia="e1")
        r2 = relacao("B", "C", evidencia="e2")

        evidencia = consolidar(
            analise([r1, r2])
        ).sucesso

        self.assertEqual(
            evidencia.relacoes,
            (r1, r2),
        )

    def test_27_none_e_string_none_preservados(self):
        evidencia = consolidar(
            analise([
                relacao("A", "B", ciclo=None),
                relacao("B", "C", ciclo="None"),
            ])
        ).sucesso

        self.assertEqual(
            evidencia.relacoes_por_ciclo[None],
            1,
        )
        self.assertEqual(
            evidencia.relacoes_por_ciclo["None"],
            1,
        )

    def test_28_sem_resolucao_arquitetural(self):
        evidencia = consolidar(
            analise([
                relacao(
                    "componente_inexistente",
                    "outro",
                )
            ])
        ).sucesso

        self.assertEqual(
            evidencia.total_nos,
            2,
        )

    def test_29_nao_acessa_persistencia(self):
        modulo = importlib.import_module(
            "nixal_evidencia_operacional"
        )

        self.assertNotIn(
            "nixal_persistencia_operacional",
            modulo.__dict__,
        )

    def test_30_dados_consolidados_equivalentes(self):
        relacoes = [
            relacao("A", "B", evidencia="e1"),
            relacao("B", "C", evidencia="e2"),
            relacao("C", "D", evidencia="e3"),
        ]

        evidencia = consolidar(
            analise(relacoes)
        ).sucesso

        self.assertEqual(
            evidencia.total_relacoes,
            len(relacoes),
        )
        self.assertEqual(
            sum(evidencia.autoridades.values()),
            len(relacoes),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
