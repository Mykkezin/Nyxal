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


def _ecdsa_fixture(curva: str = "nistp256") -> str:
    pontos_geradores = {
        "nistp256": (
            "046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296"
            "4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5"
        ),
        "nistp384": (
            "04aa87ca22be8b05378eb1c71ef320ad746e1d3b628ba79b9859f741e082542a385502f25"
            "dbf55296c3a545e3872760ab73617de4a96262c6f5d9e98bf9292dc29f8f41dbd289a147c"
            "e9da3113b5f0b8c00a60b1ce1d7e819d7a431d7c90ea0e5f"
        ),
        "nistp521": (
            "0400c6858e06b70404e9cd9e3ecb662395b4429c648139053fb521f828af606b4d3dbaa14"
            "b5e77efe75928fe1dc127a2ffa8de3348b3c1856a429bf97e7e31c2e5bd66"
            "011839296a789a3bc0045c8a5fb42c7d1bd998f54449579b446817afbd17273e662c97ee72"
            "995ef42640c550b9013fad0761353c7086a272c24088be94769fd16650"
        ),
    }
    tipo = "ecdsa-sha2-" + curva
    blob = (
        _ssh_string(tipo.encode("ascii"))
        + _ssh_string(curva.encode("ascii"))
        + _ssh_string(bytes.fromhex(pontos_geradores[curva]))
    )
    return tipo + " " + base64.b64encode(blob).decode("ascii")


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

    def test_aceita_chave_ecdsa_p384_com_ponto_valido(self) -> None:
        key = _ecdsa_fixture("nistp384")
        self.assertEqual(VpsNyxOS._validar_chave_ssh(key), key)

    def test_aceita_chave_ecdsa_p521_com_ponto_valido(self) -> None:
        key = _ecdsa_fixture("nistp521")
        self.assertEqual(VpsNyxOS._validar_chave_ssh(key), key)

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
