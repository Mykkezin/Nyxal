from __future__ import annotations

import dataclasses
import importlib
import inspect
import unittest
from dataclasses import dataclass

from nixal_padroes_recorrentes_operacional import (
    detectar,
)

from nixal_candidato_aprendizado_operacional import (
    CandidatoAprendizado,
    formular,
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


class TesteCandidatoAprendizadoOperacional(unittest.TestCase):

    def setUp(self):
        r1 = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c1",
        )

        r2 = RelacaoTeste(
            "A",
            "B",
            "observacao",
            "observacional",
            "c2",
        )

        e1 = EvidenciaTeste(
            "ev-001",
            "qualificada",
            (r1,),
        )

        e2 = EvidenciaTeste(
            "ev-002",
            "qualificada",
            (r2,),
        )

        resultado = detectar(
            (e1, e2)
        )

        self.padrao = resultado.padroes[0]
        self.resultado_o13 = resultado

    def test_01_padrao_valido_produz_candidato(self):
        candidatos = formular(
            (self.padrao,)
        )

        self.assertEqual(
            len(candidatos),
            1,
        )

        self.assertIsInstance(
            candidatos[0],
            CandidatoAprendizado,
        )

    def test_02_entrada_vazia_rejeitada(self):
        with self.assertRaises(ValueError):
            formular(())

    def test_03_tipo_invalido_rejeitado(self):
        with self.assertRaises(ValueError):
            formular(123)

    def test_04_assinatura_ausente_rejeitada(self):
        @dataclass(frozen=True)
        class SemAssinatura:
            ocorrencias: tuple
            evidencias_distintas: tuple
            frequencia_evidencias: int

        invalido = SemAssinatura(
            (),
            ("a", "b"),
            2,
        )

        with self.assertRaises(ValueError):
            formular((invalido,))

    def test_05_assinatura_vazia_rejeitada(self):
        @dataclass(frozen=True)
        class AssinaturaVazia:
            assinatura: tuple
            ocorrencias: tuple
            evidencias_distintas: tuple
            frequencia_evidencias: int

        invalido = AssinaturaVazia(
            (),
            (1,),
            ("a", "b"),
            2,
        )

        with self.assertRaises(ValueError):
            formular((invalido,))

    def test_06_sem_ocorrencias_rejeitado(self):
        @dataclass(frozen=True)
        class SemOcorrencias:
            assinatura: tuple
            ocorrencias: tuple
            evidencias_distintas: tuple
            frequencia_evidencias: int

        invalido = SemOcorrencias(
            ("A",),
            (),
            ("a", "b"),
            2,
        )

        with self.assertRaises(ValueError):
            formular((invalido,))

    def test_07_frequencia_menor_que_dois(self):
        @dataclass(frozen=True)
        class FrequenciaBaixa:
            assinatura: tuple
            ocorrencias: tuple
            evidencias_distintas: tuple
            frequencia_evidencias: int

        invalido = FrequenciaBaixa(
            ("A",),
            (1,),
            ("a",),
            1,
        )

        with self.assertRaises(ValueError):
            formular((invalido,))

    def test_08_evidencias_insuficientes(self):
        @dataclass(frozen=True)
        class EvidenciasInsuficientes:
            assinatura: tuple
            ocorrencias: tuple
            evidencias_distintas: tuple
            frequencia_evidencias: int

        invalido = EvidenciasInsuficientes(
            ("A",),
            (1,),
            ("a",),
            1,
        )

        with self.assertRaises(ValueError):
            formular((invalido,))

    def test_09_frequencia_incompativel(self):
        @dataclass(frozen=True)
        class FrequenciaIncompativel:
            assinatura: tuple
            ocorrencias: tuple
            evidencias_distintas: tuple
            frequencia_evidencias: int

        invalido = FrequenciaIncompativel(
            ("A",),
            (1,),
            ("a", "b"),
            3,
        )

        with self.assertRaises(ValueError):
            formular((invalido,))

    def test_10_preserva_assinatura(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.assinatura,
            self.padrao.assinatura,
        )

    def test_11_preserva_ocorrencias(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.ocorrencias,
            self.padrao.ocorrencias,
        )

    def test_12_preserva_evidencias(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.evidencias_distintas,
            self.padrao.evidencias_distintas,
        )

    def test_13_preserva_ciclos(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.ciclos_observados,
            self.padrao.ciclos_observados,
        )

    def test_14_preserva_frequencia(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.frequencia_evidencias,
            self.padrao.frequencia_evidencias,
        )

    def test_15_estado_candidato(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.estado,
            "candidato",
        )

    def test_16_justificativa_observacional(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertIn(
            "evidências distintas",
            candidato.justificativa,
        )

        self.assertIn(
            "não representa aprendizado",
            candidato.justificativa,
        )

    def test_17_identidade_deterministica(self):
        a = formular(
            (self.padrao,)
        )[0]

        b = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            a.identidade,
            b.identidade,
        )

    def test_18_mesma_entrada_mesmo_candidato(self):
        a = formular(
            (self.padrao,)
        )

        b = formular(
            (self.padrao,)
        )

        self.assertEqual(a, b)

    def test_19_padroes_diferentes_produzem_ids_diferentes(self):
        @dataclass(frozen=True)
        class PadraoFake:
            assinatura: tuple
            ocorrencias: tuple
            evidencias_distintas: tuple
            ciclos_observados: tuple
            frequencia_evidencias: int

        p2 = PadraoFake(
            ("X", "Y", "tipo", "autoridade"),
            (object(), object()),
            ("x", "y"),
            ("c1",),
            2,
        )

        a = formular(
            (self.padrao,)
        )[0]

        b = formular(
            (p2,)
        )[0]

        self.assertNotEqual(
            a.identidade,
            b.identidade,
        )

    def test_20_ordem_preservada(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.ocorrencias,
            self.padrao.ocorrencias,
        )

    def test_21_candidato_imutavel(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            candidato.estado = "aprendido"

    def test_22_padrao_origem_nao_modificado(self):
        antes = self.padrao

        formular((self.padrao,))

        depois = self.padrao

        self.assertEqual(
            antes,
            depois,
        )

    def test_23_ocorrencias_nao_modificadas(self):
        antes = self.padrao.ocorrencias

        formular((self.padrao,))

        self.assertEqual(
            antes,
            self.padrao.ocorrencias,
        )

    def test_24_nenhuma_relacao_nova(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.ocorrencias,
            self.padrao.ocorrencias,
        )

    def test_25_nao_cria_causalidade(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertNotIn(
            "causal",
            repr(candidato).lower(),
        )

    def test_26_nao_cria_generalizacao(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertNotIn(
            "general",
            repr(candidato).lower(),
        )

    def test_27_nao_cria_aprendizado(self):
        candidato = formular(
            (self.padrao,)
        )[0]

        self.assertEqual(
            candidato.estado,
            "candidato",
        )

        self.assertFalse(
            hasattr(candidato, "aprendizado"),
        )

        self.assertFalse(
            hasattr(candidato, "memoria_aprendida"),
        )

    def test_28_nao_executa_llc(self):
        modulo = importlib.import_module(
            "nixal_candidato_aprendizado_operacional"
        )

        nomes = set(modulo.__dict__)

        proibidos = {
            "nixal_aprendizado_llc",
            "nixal_fechamento_llc",
            "ReplicacaoLLC",
        }

        self.assertTrue(
            nomes.isdisjoint(proibidos)
        )

    def test_29_isolamento(self):
        modulo = importlib.import_module(
            "nixal_candidato_aprendizado_operacional"
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
            self.assertNotIn(
                item,
                fonte,
            )

    def test_30_compatibilidade_o13_o14(self):
        resultado = self.resultado_o13

        candidatos = formular(
            resultado.padroes
        )

        self.assertEqual(
            len(candidatos),
            resultado.total_padroes,
        )

        for candidato, padrao in zip(
            candidatos,
            sorted(
                resultado.padroes,
                key=lambda item: (
                    "CAND-"
                    + str(item.assinatura)
                ),
            ),
        ):
            self.assertTrue(
                candidato.identidade.startswith(
                    "CAND-"
                )
            )
            self.assertEqual(
                candidato.estado,
                "candidato",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
