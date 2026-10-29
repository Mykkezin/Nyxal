import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nixal_capacidades as nc


class TestInicializacaoCapacidades(unittest.TestCase):
    def test_inicializacao_preserva_catalogo_existente(self):
        original = b'[{"nome":"evidencia_preexistente"}]\n'

        with tempfile.TemporaryDirectory() as temp:
            catalogo = Path(temp) / "capacidades_nixal.json"
            catalogo.write_bytes(original)

            with patch.object(nc, "ARQUIVO_CAPACIDADES", catalogo):
                nc.GerenciadorCapacidades()

            self.assertEqual(catalogo.read_bytes(), original)

    def test_inicializacao_nao_cria_catalogo_ausente(self):
        with tempfile.TemporaryDirectory() as temp:
            catalogo = Path(temp) / "ausente.json"

            with patch.object(nc, "ARQUIVO_CAPACIDADES", catalogo):
                nc.GerenciadorCapacidades()

            self.assertFalse(catalogo.exists())

    def test_registro_explicito_persiste_nova_capacidade(self):
        with tempfile.TemporaryDirectory() as temp:
            catalogo = Path(temp) / "capacidades_nixal.json"
            catalogo.write_bytes(b"[]")

            with patch.object(nc, "ARQUIVO_CAPACIDADES", catalogo):
                gerente = nc.GerenciadorCapacidades()
                gerente.registrar(
                    nome="teste_persistencia_explicita",
                    descricao="Capacidade de regressao.",
                    objetivo="Validar persistencia explicita.",
                    exemplos=["Executar teste."],
                    funcao=lambda: {"sucesso": True},
                    dominios=["teste"],
                    evidencias_dominio=["regressao"],
                )

                dados = json.loads(catalogo.read_text(encoding="utf-8"))

            self.assertTrue(any(
                item.get("nome") == "teste_persistencia_explicita"
                for item in dados
            ))

    def test_catalogo_invalido_nao_e_sobrescrito(self):
        evidencia = b'{"incompleto":'

        with tempfile.TemporaryDirectory() as temp:
            catalogo = Path(temp) / "capacidades_nixal.json"
            catalogo.write_bytes(evidencia)

            with patch.object(nc, "ARQUIVO_CAPACIDADES", catalogo):
                gerente = nc.GerenciadorCapacidades()
                gerente.registrar(
                    nome="teste_catalogo_invalido",
                    descricao="Capacidade de regressao.",
                    objetivo="Preservar evidencia.",
                    exemplos=["Teste."],
                    funcao=lambda: {"sucesso": True},
                    dominios=["teste"],
                    evidencias_dominio=["regressao"],
                )

            self.assertEqual(catalogo.read_bytes(), evidencia)


if __name__ == "__main__":
    unittest.main()
