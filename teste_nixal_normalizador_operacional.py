import builtins
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nixal_normalizador_operacional import (  # noqa: E402
    NormalizadorOperacional,
)


TS = "2026-10-07T10:00:00-03:00"


def base(fonte):
    return {
        "fonte": fonte,
        "origem": fonte + "_origem",
        "proveniencia": {
            "habitat": "nixal_habitat.py",
            "persistencia": "nixal_persistencia_operacional.py",
            "delta": "nixal_delta.py",
            "ae4": "nixal_ciclo_evolucao_ae4.py",
        }[fonte],
        "evidencia": fonte + "_evidencia",
        "instante": TS,
    }


class TestNormalizadorOperacional(unittest.TestCase):
    def setUp(self):
        self.n = NormalizadorOperacional()

    def test_normalizar_habitat_valido(self):
        e = base("habitat")
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.tipo, "observacao")
        self.assertEqual(r.relacao.autoridade, "observacional")
        self.assertIsNone(r.relacao.ciclo)
        self.assertEqual(r.relacao.destino, None)

    def test_normalizar_persistencia_valida(self):
        e = base("persistencia")
        e["ciclo_id"] = "ciclo-01"
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.tipo, "persistencia")
        self.assertEqual(r.relacao.ciclo, "ciclo-01")

    def test_normalizar_delta_valido(self):
        e = base("delta")
        e.update(
            {
                "delta_id": "Δ-abc",
                "tipo": "transformacao",
                "estado_anterior": "a",
                "estado_novo": "b",
                "evidencias": ["ev-1"],
                "ciclo": "ciclo-delta",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "arquitetura_modificada": False,
            }
        )
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.tipo, "transformacao")
        self.assertEqual(r.relacao.autoridade, "observacional")
        self.assertEqual(r.relacao.ciclo, "ciclo-delta")

    def test_normalizar_ae4_observacional(self):
        e = base("ae4")
        e.update(
            {
                "relacao_confirmada": False,
                "tipo_relacao": "observacional",
                "ciclo_id": "ae4-01",
            }
        )
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.tipo, "observacao")
        self.assertEqual(r.relacao.autoridade, "observacional")

    def test_normalizar_ae4_experimental(self):
        e = base("ae4")
        e.update(
            {
                "relacao_confirmada": True,
                "vinculo_causal_persistido": True,
                "avaliacao_concluida": True,
                "resultado_classificado": "melhoria_comprovada",
                "stable_modificada": False,
                "integracao_executada": False,
                "ciclo_id": "ae4-exp-01",
            }
        )
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.tipo, "evidencia_experimental")
        self.assertEqual(r.relacao.autoridade, "experimental")

    def test_rejeitar_origem_vazia_ou_ausente(self):
        for origem in ("", None):
            e = base("habitat")
            e["origem"] = origem
            r = self.n.normalizar(e)
            self.assertFalse(r.sucesso)
            self.assertEqual(r.rejeicao.codigo, "campo_obrigatorio_ausente")

    def test_rejeitar_tipo_desconhecido(self):
        e = base("delta")
        e["tipo"] = "tipo_inventado"
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.tipo, "transformacao")

    def test_rejeitar_ciclo_inventado(self):
        e = base("persistencia")
        e["ciclo_id"] = 42
        with self.assertRaises(ValueError):
            self.n.normalizar(e)

    def test_rejeitar_tentativa_autoridade_arquitetural(self):
        e = base("habitat")
        e["autoridade"] = "arquitetural"
        r = self.n.normalizar(e)
        self.assertFalse(r.sucesso)
        self.assertEqual(r.rejeicao.codigo, "autoridade_proibida")

    def test_rejeitar_tentativa_autorizacao_falsa(self):
        e = base("delta")
        e.update(
            {
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "arquitetura_modificada": False,
            }
        )
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.autoridade, "observacional")

    def test_relacao_imutavel(self):
        e = base("habitat")
        r = self.n.normalizar(e)
        with self.assertRaises((AttributeError, TypeError)):
            r.relacao.tipo = "transformacao"

    def test_conservacao_epistemologica(self):
        e = base("delta")
        e.update(
            {
                "delta_id": "Δ-conservacao",
                "ciclo": "ciclo-02",
                "autorizacao_explicita": False,
                "integracao_executada": False,
            }
        )
        original = copy.deepcopy(e)
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(e, original)
        self.assertEqual(r.relacao.autoridade, "observacional")
        self.assertNotEqual(r.relacao.tipo, "evidencia_experimental")

    def test_isolamento_sem_efeitos_colaterais(self):
        e = base("habitat")
        original = copy.deepcopy(e)
        before = set(Path(".").iterdir())
        real_open = builtins.open

        def forbidden_open(*args, **kwargs):
            raise AssertionError("normalizador tentou acessar o filesystem")

        builtins.open = forbidden_open
        try:
            r = self.n.normalizar(e)
        finally:
            builtins.open = real_open

        after = set(Path(".").iterdir())
        self.assertTrue(r.sucesso)
        self.assertEqual(e, original)
        self.assertEqual(before, after)

    def test_destino_so_quando_demonstrado(self):
        e = base("habitat")
        e["destino"] = "pid-123"
        r = self.n.normalizar(e)
        self.assertFalse(r.sucesso)
        self.assertEqual(r.rejeicao.codigo, "destino_invalido")

        e["destino_demonstrado"] = True
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.destino, "pid-123")

    def test_ciclo_ausente_permanece_null(self):
        for fonte in ("habitat", "persistencia", "delta", "ae4"):
            e = base(fonte)
            r = self.n.normalizar(e)
            self.assertTrue(r.sucesso)
            self.assertIsNone(r.relacao.ciclo)

    def test_proveniencia_invalida(self):
        e = base("habitat")
        e["proveniencia"] = "modulo_inventado.py"
        r = self.n.normalizar(e)
        self.assertFalse(r.sucesso)
        self.assertEqual(r.rejeicao.codigo, "proveniencia_invalida")

    def test_timestamp_invalido(self):
        e = base("habitat")
        e["instante"] = "nao-e-data"
        r = self.n.normalizar(e)
        self.assertFalse(r.sucesso)
        self.assertEqual(r.rejeicao.codigo, "instante_invalido")

    def test_evidencia_ausente(self):
        e = base("habitat")
        del e["evidencia"]
        r = self.n.normalizar(e)
        self.assertFalse(r.sucesso)
        self.assertEqual(r.rejeicao.codigo, "evidencia_ambigua")

    def test_hash_de_evidencia(self):
        e = base("habitat")
        del e["evidencia"]
        e["evidencia_hash"] = "sha256:abc123"
        r = self.n.normalizar(e)
        self.assertTrue(r.sucesso)
        self.assertEqual(r.relacao.evidencia, "sha256:abc123")


if __name__ == "__main__":
    unittest.main()
