#!/usr/bin/env python3
from __future__ import annotations

import base64
import unittest

from nixal_vps import VpsNyxOS


def _ssh_string(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def _ed25519_fixture() -> str:
    blob = _ssh_string(b"ssh-ed25519") + _ssh_string(bytes(range(32)))
    return "ssh-ed25519 " + base64.b64encode(blob).decode("ascii") + " nyxal-test-comment"


def _ecdsa_fixture() -> str:
    ponto_gerador_p256 = bytes.fromhex(
        "046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296"
        "4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5"
    )
    blob = (
        _ssh_string(b"ecdsa-sha2-nistp256")
        + _ssh_string(b"nistp256")
        + _ssh_string(ponto_gerador_p256)
    )
    return "ecdsa-sha2-nistp256 " + base64.b64encode(blob).decode("ascii")


def _rsa_fixture(bits: int = 2048, exponent: bytes = b"\x01\x00\x01") -> str:
    modulus_bytes = (bits + 7) // 8
    modulus_value = (1 << (bits - 1)) | 1
    modulus = modulus_value.to_bytes(modulus_bytes, "big")
    if modulus[0] & 0x80:
        modulus = b"\x00" + modulus
    blob = _ssh_string(b"ssh-rsa") + _ssh_string(exponent) + _ssh_string(modulus)
    return "ssh-rsa " + base64.b64encode(blob).decode("ascii")


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

    def test_aceita_chave_ed25519_estruturalmente_valida_e_remove_comentario(self) -> None:
        key = _ed25519_fixture()
        normalized = VpsNyxOS._validar_chave_ssh(key)
        self.assertEqual(normalized.split(), key.split()[:2])
        self.assertNotIn("nyxal-test-comment", normalized)

    def test_aceita_chave_ecdsa_p256_estruturalmente_valida(self) -> None:
        key = _ecdsa_fixture()
        self.assertEqual(VpsNyxOS._validar_chave_ssh(key), key)

    def test_aceita_rsa_com_minimo_de_2048_bits_e_expoente_valido(self) -> None:
        chave = _rsa_fixture(2048)
        self.assertEqual(VpsNyxOS._validar_chave_ssh(chave), chave)

    def test_rejeita_rsa_fraco_ou_expoente_invalido(self) -> None:
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS._validar_chave_ssh(_rsa_fixture(1024))
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS._validar_chave_ssh(_rsa_fixture(2048, b"\x02"))

    def test_rejeita_quebras_de_linha_que_poderiam_injetar_cloud_init(self) -> None:
        key = _ed25519_fixture()
        malicious = key + "\n  runcmd:\n    - touch /tmp/nyxal-ssh-injection"
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS._validar_chave_ssh(malicious)

    def test_rejeita_ponto_ecdsa_fora_da_curva(self) -> None:
        blob = (
            _ssh_string(b"ecdsa-sha2-nistp256")
            + _ssh_string(b"nistp256")
            + _ssh_string(b"\\x04" + bytes(range(64)))
        )
        key = "ecdsa-sha2-nistp256 " + base64.b64encode(blob).decode("ascii")
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS._validar_chave_ssh(key)

    def test_rejeita_base64_invalido_e_tipo_de_chave_incoerente(self) -> None:
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS._validar_chave_ssh("ssh-ed25519 not-base64***")
        blob = _ssh_string(b"ssh-rsa") + _ssh_string(b"e") + _ssh_string(b"n" * 128)
        key = "ssh-ed25519 " + base64.b64encode(blob).decode("ascii")
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS._validar_chave_ssh(key)

    def test_provisionamento_rejeita_chave_invalida_antes_de_acessar_imagem(self) -> None:
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS().provisionar(
                nome="vps-teste",
                image_path="/caminho/inexistente.img",
                ssh_public_key=_ed25519_fixture() + "\n  runcmd: [malicious]",
            )


    def test_cloud_init_sink_rejeita_chave_maliciosa_antes_de_invocar_ferramentas(self) -> None:
        with self.assertRaisesRegex(ValueError, "ssh_public_key_invalida"):
            VpsNyxOS()._criar_cloud_init(
                nome="vps-teste",
                username="ubuntu",
                ssh_public_key=_ed25519_fixture() + "\n  runcmd: [malicious]",
            )


if __name__ == "__main__":
    unittest.main()
