#!/usr/bin/env python3
"""Deterministic, non-provisioning regressions for the DELTA MVP-0 helpers."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import tempfile
import unittest
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

DELTA_DIR = Path(__file__).resolve().parent
SCRIPT = DELTA_DIR / "criar_vm_mvp0.py"
SPEC = importlib.util.spec_from_file_location("delta_criar_vm_mvp0", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Não foi possível carregar o helper MVP-0")
delta_vm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delta_vm)


class TesteCriacaoGuardadaVMDelta(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_run_usa_argv_sem_shell(self) -> None:
        comando = ["virsh", "dominfo", "nome; touch /tmp/nyxal-pwned"]
        fake = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(delta_vm.subprocess, "run", return_value=fake) as run:
            result = delta_vm.run(comando)
        self.assertIs(result, fake)
        args, kwargs = run.call_args
        self.assertEqual(args[0], comando)
        self.assertFalse(kwargs.get("shell", False))

    def test_rejeita_nome_invalido_antes_de_consultar_host(self) -> None:
        with (
            patch.object(delta_vm.sys, "argv", ["criar_vm_mvp0.py", "--name", "delta; touch /tmp/pwned"]),
            patch.object(delta_vm, "require_tool") as require_tool,
            patch.object(delta_vm, "run") as run,
            patch("sys.stderr", new=io.StringIO()),
        ):
            result = delta_vm.main()
        self.assertEqual(result, 2)
        require_tool.assert_not_called()
        run.assert_not_called()

    def test_rejeita_armazenamento_dentro_da_home(self) -> None:
        home = self.root / "home"
        home.mkdir()
        destino = home / "NyxOS" / "VPS"
        with (
            patch.object(delta_vm.sys, "argv", ["criar_vm_mvp0.py", "--storage", str(destino)]),
            patch.object(delta_vm.Path, "home", return_value=home),
            patch.dict(os.environ, {"NYXOS_VPS_LIBVIRT_URI": "qemu:///system"}),
            patch.object(delta_vm, "require_tool") as require_tool,
            patch("sys.stderr", new=io.StringIO()),
        ):
            result = delta_vm.main()
        self.assertEqual(result, 2)
        require_tool.assert_not_called()
        self.assertFalse(destino.exists())

    def test_valida_chave_publica_sem_criar_chave_privada(self) -> None:
        ssh_dir = self.root / ".ssh"
        ssh_dir.mkdir()
        key = ssh_dir / "id_ed25519.pub"
        key.write_text("ssh-ed25519 QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo= test-comment\n", encoding="utf-8")
        fake = SimpleNamespace(returncode=0, stdout="256 SHA256:test (ED25519)", stderr="")
        with patch.object(delta_vm.Path, "home", return_value=self.root), patch.object(delta_vm, "require_tool"), patch.object(delta_vm, "run", return_value=fake) as run:
            result = delta_vm.find_ssh_key(None)
        self.assertEqual(result, key.resolve())
        self.assertEqual(run.call_args.args[0][0], "ssh-keygen")
        self.assertTrue(key.is_file())
        self.assertFalse((ssh_dir / "id_ed25519").exists())

    def test_chave_publica_com_multiplas_linhas_e_rejeitada(self) -> None:
        key = self.root / "publicas.pub"
        key.write_text("ssh-ed25519 QUJD comment\nssh-ed25519 Rk9P comment\n", encoding="utf-8")
        with patch.object(delta_vm.Path, "home", return_value=self.root), patch.object(delta_vm, "require_tool"), patch.object(delta_vm, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "exatamente_uma_chave_publica"):
                delta_vm.find_ssh_key(str(key))
        run.assert_not_called()

    def test_verifica_sha256_e_nome_canonico_da_imagem(self) -> None:
        image = self.root / delta_vm.DEFAULT_IMAGE_NAME
        image.write_bytes(b"fixture cloud image")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        Path(str(image) + ".sha256").write_text(f"{digest}  {image.name}\n", encoding="utf-8")
        fake = SimpleNamespace(returncode=0, stdout=f"{digest}  {image}\n", stderr="")
        with patch.object(delta_vm, "require_tool"), patch.object(delta_vm, "run", return_value=fake) as run:
            result = delta_vm.verify_image(image)
        self.assertEqual(result, digest)
        self.assertEqual(run.call_args.args[0][0], "sha256sum")

    def test_hash_incorreto_bloqueia_criacao(self) -> None:
        image = self.root / delta_vm.DEFAULT_IMAGE_NAME
        image.write_bytes(b"tampered image")
        Path(str(image) + ".sha256").write_text(f"{'0' * 64}  {image.name}\n", encoding="utf-8")
        fake = SimpleNamespace(returncode=0, stdout=f"{'1' * 64}  {image}\n", stderr="")
        with patch.object(delta_vm, "require_tool"), patch.object(delta_vm, "run", return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "SHA256_da_imagem_nao_confere"):
                delta_vm.verify_image(image)

    def test_rejeita_rede_libvirt_inativa(self) -> None:
        responses = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout="Name: default\nActive: no\n", stderr=""),
        ]
        with patch.object(delta_vm, "require_tool"), patch.object(delta_vm, "run", side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, "rede_libvirt_default_nao_ativa"):
                delta_vm.check_libvirt("delta-mvp0")

    def test_bloqueia_nome_de_dominio_ja_existente(self) -> None:
        responses = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout="Name: default\nActive: yes\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="Name: delta-mvp0\n", stderr=""),
        ]
        with patch.object(delta_vm, "require_tool"), patch.object(delta_vm, "run", side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, "dominio_ja_existe"):
                delta_vm.check_libvirt("delta-mvp0")

    def test_cancelamento_interativo_nao_inicia_provisionador(self) -> None:
        home = self.root / "home"
        home.mkdir()
        storage = self.root / "storage-outside-home"
        storage.mkdir()
        key = home / "id_ed25519.pub"
        key.write_text("ssh-ed25519 QUJD comment\n", encoding="utf-8")
        fake_stdin = SimpleNamespace(isatty=lambda: True)
        fake_module = types.ModuleType("nixal_vps")
        fake_vps_class = Mock()
        fake_module.VpsNyxOS = fake_vps_class
        with (
            patch.object(delta_vm.sys, "argv", ["criar_vm_mvp0.py", "--storage", str(storage)]),
            patch.object(delta_vm.sys, "stdin", fake_stdin),
            patch.object(delta_vm.Path, "home", return_value=home),
            patch.dict(os.environ, {"NYXOS_VPS_LIBVIRT_URI": "qemu:///system"}),
            patch.object(delta_vm, "require_tool"),
            patch.object(delta_vm.shutil, "which", return_value="/usr/bin/getfacl"),
            patch.object(delta_vm, "run", return_value=SimpleNamespace(
                    returncode=0,
                    stdout="user:libvirt-qemu:rwx\ndefault:user:libvirt-qemu:rwx\n",
                    stderr="",
                )) as run,
            patch.dict(sys.modules, {"nixal_vps": fake_module}),
            patch.object(delta_vm, "find_ssh_key", return_value=key),
            patch.object(delta_vm, "verify_image", return_value="a" * 64),
            patch.object(delta_vm, "check_libvirt"),
            patch.object(delta_vm, "free_space", return_value=(100 * delta_vm.GIB, self.root)),
            patch.object(delta_vm, "run") as run,
            patch("builtins.input", return_value="n"),
            patch("sys.stdout", new=io.StringIO()),
        ):
            result = delta_vm.main()
        self.assertEqual(result, 0)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["/usr/bin/getfacl", "-cp", str(storage)])
        fake_vps_class.assert_not_called()
        self.assertEqual(list(storage.iterdir()), [])

    def test_modo_nao_interativo_aborta_sem_provisionar(self) -> None:
        home = self.root / "home-nao-interativo"
        home.mkdir()
        storage = self.root / "storage-nao-interativo"
        storage.mkdir()
        fake_stdin = SimpleNamespace(isatty=lambda: False)
        fake_module = types.ModuleType("nixal_vps")
        fake_vps_class = Mock()
        fake_module.VpsNyxOS = fake_vps_class
        with (
            patch.object(delta_vm.sys, "argv", [
                "criar_vm_mvp0.py", "--storage", str(storage),
                "--image", str(self.root / delta_vm.DEFAULT_IMAGE_NAME),
            ]),
            patch.object(delta_vm.sys, "stdin", fake_stdin),
            patch.object(delta_vm.sys, "path", list(delta_vm.sys.path)),
            patch.object(delta_vm.Path, "home", return_value=home),
            patch.dict(os.environ, {"NYXOS_VPS_LIBVIRT_URI": "qemu:///system"}, clear=False),
            patch.dict(sys.modules, {"nixal_vps": fake_module}),
            patch.object(delta_vm, "require_tool"),
            patch.object(delta_vm.shutil, "which", return_value="/usr/bin/getfacl"),
            patch.object(delta_vm, "run", return_value=SimpleNamespace(
                    returncode=0,
                    stdout="user:libvirt-qemu:rwx\ndefault:user:libvirt-qemu:rwx\n",
                    stderr="",
                )),
            patch.object(delta_vm, "find_ssh_key", return_value=self.root / "id_ed25519.pub"),
            patch.object(delta_vm, "verify_image", return_value="a" * 64),
            patch.object(delta_vm, "check_libvirt"),
            patch.object(delta_vm, "free_space", return_value=(100 * delta_vm.GIB, self.root)),
            patch("builtins.input", return_value="s") as prompt,
            patch("sys.stdout", new=io.StringIO()),
            patch("sys.stderr", new=io.StringIO()),
        ):
            result = delta_vm.main()
        self.assertEqual(result, 2)
        prompt.assert_not_called()
        fake_vps_class.assert_not_called()
        self.assertEqual(list(storage.iterdir()), [])

    def test_confirmacao_positiva_chama_provisionador_existente(self) -> None:
        home = self.root / "home-interativo"
        home.mkdir()
        storage = self.root / "storage-interativo"
        storage.mkdir()
        key = self.root / "key.pub"
        key.write_text("ssh-ed25519 QUJDREVGR0g= comentario-livre\n", encoding="utf-8")
        fake_stdin = SimpleNamespace(isatty=lambda: True)
        provisionar = __import__("unittest.mock", fromlist=["Mock"]).Mock(
            return_value={"sucesso": True}
        )
        instancia_vps = SimpleNamespace(provisionar=provisionar)
        fake_vps_class = Mock(return_value=instancia_vps)
        fake_module = types.ModuleType("nixal_vps")
        fake_module.VpsNyxOS = fake_vps_class
        with (
            patch.object(delta_vm.sys, "argv", [
                "criar_vm_mvp0.py", "--storage", str(storage),
                "--image", str(self.root / delta_vm.DEFAULT_IMAGE_NAME),
            ]),
            patch.object(delta_vm.sys, "stdin", fake_stdin),
            patch.object(delta_vm.sys, "path", list(delta_vm.sys.path)),
            patch.object(delta_vm.Path, "home", return_value=home),
            patch.dict(os.environ, {"NYXOS_VPS_LIBVIRT_URI": "qemu:///system"}, clear=False),
            patch.dict(sys.modules, {"nixal_vps": fake_module}),
            patch.object(delta_vm, "require_tool"),
            patch.object(delta_vm.shutil, "which", return_value="/usr/bin/getfacl"),
            patch.object(delta_vm, "run", return_value=SimpleNamespace(
                    returncode=0,
                    stdout="user:libvirt-qemu:rwx\ndefault:user:libvirt-qemu:rwx\n",
                    stderr="",
                )) as run,
            patch.object(delta_vm, "find_ssh_key", return_value=key),
            patch.object(delta_vm, "verify_image", return_value="a" * 64),
            patch.object(delta_vm, "check_libvirt"),
            patch.object(delta_vm, "free_space", return_value=(100 * delta_vm.GIB, self.root)),
            patch("builtins.input", return_value="s") as prompt,
            patch("sys.stdout", new=io.StringIO()),
            patch("sys.stderr", new=io.StringIO()),
        ):
            result = delta_vm.main()
        self.assertEqual(result, 0)
        prompt.assert_called_once()
        fake_vps_class.assert_called_once_with()
        provisionar.assert_called_once()
        kwargs = provisionar.call_args.kwargs
        self.assertEqual(kwargs["ssh_public_key"], "ssh-ed25519 QUJDREVGR0g=")
        self.assertFalse(kwargs["autostart"])
        self.assertEqual(kwargs["nome"], "delta-mvp0")
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["/usr/bin/getfacl", "-cp", str(storage)])
        self.assertEqual(list(storage.iterdir()), [])

    def test_storage_helper_exige_confirmacao_antes_da_alteracao(self) -> None:
        source = (DELTA_DIR / "preparar_storage_mvp0.sh").read_text(encoding="utf-8")
        prompt = source.index('read -r -p "Prosseguir? Digite')
        create = source.index('sudo mkdir -m 0700 -- "${TARGET}"')
        owner = source.index('sudo chown "$(id -un):${QEMU_GROUP}" -- "${TARGET}"')
        mode = source.index('sudo chmod 2770 -- "${TARGET}"')
        acl = source.index("sudo setfacl -m")
        self.assertLess(prompt, create)
        self.assertLess(create, owner)
        self.assertLess(owner, mode)
        self.assertLess(mode, acl)
        self.assertNotIn("sudo install -d", source)
        self.assertNotIn("chmod 777", source)
        self.assertNotIn("virsh net-start", source)

    def test_scripts_de_preflight_e_diagnostico_sao_somente_leitura(self) -> None:
        preflight = (DELTA_DIR / "preflight_vm.sh").read_text(encoding="utf-8")
        self.assertIn('VM_STORAGE="${NYXOS_DELTA_VM_STORAGE:-${NYXOS_VPS_STORAGE:-${HOME}/NyxOS/VPS}}"', preflight)
        diagnose = (DELTA_DIR / "diagnosticar_vm_mvp0.sh").read_text(encoding="utf-8")
        for forbidden in ("apt install", "apt-get install", "virsh net-start", "systemctl start", "rm -rf"):
            self.assertNotIn(forbidden, preflight)
            self.assertNotIn(forbidden, diagnose)


if __name__ == "__main__":
    unittest.main(verbosity=2)
