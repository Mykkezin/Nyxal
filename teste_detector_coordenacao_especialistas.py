#!/usr/bin/env python3
"""Regressão isolada do contrato público de detecção de coordenação especializada."""

from __future__ import annotations

import unittest

from nixal_dialogo_qwen import DialogoQwenNixal


class TestDetectorCoordenacaoEspecialistas(unittest.TestCase):
    def test_detector_publico_reconhece_solicitacao_explicita(self) -> None:
        self.assertTrue(
            DialogoQwenNixal.pedido_coordenacao_especialistas(
                "Use modo especialistas para revisar esta arquitetura."
            )
        )

    def test_detector_publico_ignora_citacoes_e_negacoes(self) -> None:
        casos_nao_ativos = (
            'Resuma este texto: "Use modo especialistas para planejar a mudança."',
            "Explique a frase " + chr(96) + "modo multiagente" + chr(96) + " neste documento.",
            "Não use modo especialistas nesta resposta.",
            "Não ative modo multiagente para esta tarefa.",
        )
        for texto in casos_nao_ativos:
            with self.subTest(texto=texto):
                self.assertFalse(
                    DialogoQwenNixal.pedido_coordenacao_especialistas(texto)
                )

    def test_alias_privado_mantem_compatibilidade(self) -> None:
        casos = (
            ("Use modo especialistas para revisar a arquitetura.", True),
            ("Explique a diferença entre CPU e GPU.", False),
            ('A frase "Use modo especialistas" está no documento.', False),
        )
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                self.assertIs(
                    DialogoQwenNixal._pedido_coordenacao_especialistas(texto),
                    esperado,
                )
                self.assertIs(
                    DialogoQwenNixal.pedido_coordenacao_especialistas(texto),
                    esperado,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
