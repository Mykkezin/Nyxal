#!/usr/bin/env python3
from __future__ import annotations

import unittest

from nixal_vps import VpsNyxOS


class VpsNyxOSTest(unittest.TestCase):
    def test_contexto(self) -> None:
        contexto = VpsNyxOS().contexto()
        self.assertEqual(contexto["backend"], "libvirt_kvm")
        self.assertIn("start", contexto["acoes"])
        self.assertIn("provisionar", VpsNyxOS.__dict__)

    def test_nome_invalido(self) -> None:
        vps = VpsNyxOS()
        with self.assertRaises(ValueError):
            vps._nome_valido("nome com espaço")
        with self.assertRaises(ValueError):
            vps._nome_valido("../escape")

    def test_status_sem_virsh(self) -> None:
        vps = VpsNyxOS()
        original = vps._tool
        vps._tool = lambda _name: None
        try:
            status = vps.status()
        finally:
            vps._tool = original
        self.assertFalse(status["operacional"])
        self.assertEqual(status["motivo"], "virsh_nao_instalado")


if __name__ == "__main__":
    unittest.main()
