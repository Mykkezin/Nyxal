#!/usr/bin/env python3
from __future__ import annotations

import subprocess
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

    def test_parser_ips(self) -> None:
        vps = VpsNyxOS()
        original = vps._run
        vps._run = lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["virsh"],
            returncode=0,
            stdout=(
                "Interface  MAC                 Protocol     Address\n"
                "vnet0       aa:bb               ipv4         192.168.122.42/24\n"
            ),
            stderr="",
        )
        try:
            self.assertEqual(vps._ip_addresses("nyx-vps-01"), ["192.168.122.42/24"])
        finally:
            vps._run = original

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
