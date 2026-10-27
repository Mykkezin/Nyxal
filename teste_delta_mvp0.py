#!/usr/bin/env python3
"""Regressões seguras do utilitário interativo de bootstrap DELTA MVP-0.

Todos os testes substituem o provisionador KVM por um mock. Nenhuma VM, rede,
ACL, arquivo operacional do host ou serviço real é criado/modificado.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "deploy" / "delta" / "criar_vm_mvp0.py"
SPEC = importlib.util.spec_from_file_location("delta_criar_vm_mvp0_teste", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("não foi possível carregar o utilitário DELTA para teste")
delta = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delta)


class TerminalFalso(io.StringIO):
    def __init__(self, *, interativo: bool) -> None:
        super().__init__("")
        self.interativo = interativo

    def isatty(self) -> bool:
        return self.interativo


class TesteDeltaMVP0(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="nyxal-delta-mvp0-test-")
        self.pasta = Path(self.temp.name)
        self.storage = self.pasta / "storage-dedicado"
        self.storage.mkdir()
        self.image = self.pasta / "ubuntu-cloud.img"
        self.image.write_bytes(b"imagem-de-laboratorio-falsa")
        self.key = self.pasta / "id_ed25519.pub"
        self.key.write_text(
            "ssh-ed25519 AAAATESTKEYDATA comentario-livre\n",
            encoding="utf-8",
        )

        self.vps_instance = Mock()
        self.vps_instance.provisionar.return_value = {"sucesso": True}
        self.vps_class = Mock(return_value=self.vps_instance)
        self.fake_vps_module = types.ModuleType("nixal_vps")
        self.fake_vps_module.VpsNyxOS = self.vps_class

    def tearDown(self) -> None:
        self.temp.cleanup()

    def executar_main(
        self,
        *,
        answer: str = "n",
        interativo: bool = True,
        args_extra: tuple[str, ...] = (),
        erro_imagem: Exception | None = None,
    ) -> tuple[int, Mock, Mock]:
        args = [
            str(SCRIPT),
            "--storage", str(self.storage),
            "--image", str(self.image),
            *args_extra,
        ]
        with ExitStack() as stack:
            stack.enter_context(patch.object(delta.sys, "argv", args))
            stack.enter_context(patch.object(delta.sys, "path", list(delta.sys.path)))
            stack.enter_context(patch.object(delta.sys, "stdin", TerminalFalso(interativo=interativo)))
            input_mock = stack.enter_context(patch("builtins.input", return_value=answer))
            stack.enter_context(patch.dict(sys.modules, {"nixal_vps": self.fake_vps_module}))
            stack.enter_context(patch.dict("os.environ", {"NYXOS_VPS_LIBVIRT_URI": "qemu:///system"}, clear=False))
            stack.enter_context(patch.object(delta, "require_tool"))
            # Mock the storage ACL pre-flight; tests never inspect or modify host ACLs.
            stack.enter_context(patch.object(delta.shutil, "which", return_value="/usr/bin/getfacl"))
            stack.enter_context(patch.object(
                delta,
                "run",
                return_value=CompletedProcess(
                    args=["getfacl", "-cp", str(self.storage)],
                    returncode=0,
                    stdout="user:libvirt-qemu:rwx\ndefault:user:libvirt-qemu:rwx\n",
                    stderr="",
                ),
            ))
            stack.enter_context(patch.object(delta, "find_ssh_key", return_value=self.key))
            if erro_imagem is None:
                stack.enter_context(patch.object(delta, "verify_image", return_value="a" * 64))
            else:
                stack.enter_context(patch.object(delta, "verify_image", side_effect=erro_imagem))
            stack.enter_context(patch.object(delta, "check_libvirt"))
            stack.enter_context(
                patch.object(delta, "free_space", return_value=(20 * delta.GIB, self.pasta))
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = delta.main()
            return result, input_mock, self.vps_class

    def test_nome_invalido_aborta_antes_de_consultar_o_host(self) -> None:
        with patch.object(delta, "require_tool") as require_tool:
            with patch.object(delta.sys, "argv", [str(SCRIPT), "--name", "../escape"]):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    resultado = delta.main()
        self.assertEqual(resultado, 2)
        require_tool.assert_not_called()
        self.vps_class.assert_not_called()

    def test_modo_sem_terminal_aborta_sem_pedir_confirmacao(self) -> None:
        resultado, input_mock, vps_class = self.executar_main(interativo=False)
        self.assertEqual(resultado, 2)
        input_mock.assert_not_called()
        vps_class.assert_not_called()
        self.vps_instance.provisionar.assert_not_called()

    def test_recusa_de_confirmacao_nao_cria_vm(self) -> None:
        resultado, input_mock, vps_class = self.executar_main(answer="n")
        self.assertEqual(resultado, 0)
        input_mock.assert_called_once()
        vps_class.assert_not_called()
        self.vps_instance.provisionar.assert_not_called()

    def test_falha_de_checksum_aborta_antes_de_confirmar(self) -> None:
        resultado, input_mock, vps_class = self.executar_main(
            erro_imagem=RuntimeError("SHA256_da_imagem_nao_confere")
        )
        self.assertEqual(resultado, 2)
        input_mock.assert_not_called()
        vps_class.assert_not_called()
        self.vps_instance.provisionar.assert_not_called()

    def test_confirmacao_explicita_chama_apenas_provisionador_existente(self) -> None:
        resultado, input_mock, vps_class = self.executar_main(answer="s")
        self.assertEqual(resultado, 0)
        input_mock.assert_called_once()
        vps_class.assert_called_once_with()
        self.vps_instance.provisionar.assert_called_once()
        kwargs = self.vps_instance.provisionar.call_args.kwargs
        self.assertEqual(kwargs["nome"], "delta-mvp0")
        self.assertEqual(kwargs["image_path"], str(self.image.resolve()))
        self.assertEqual(kwargs["ssh_public_key"], "ssh-ed25519 AAAATESTKEYDATA")
        self.assertFalse(kwargs["autostart"])
        self.assertFalse(self.vps_instance.provisionar.call_args.kwargs.get("executor_autorizado", False))

    def test_verify_image_aceita_apenas_hash_correspondente_ao_sidecar(self) -> None:
        digest = hashlib.sha256(self.image.read_bytes()).hexdigest()
        sidecar = Path(str(self.image) + ".sha256")
        sidecar.write_text(f"{digest}  {self.image.name}\n", encoding="utf-8")
        with patch.object(delta, "require_tool"), patch.object(
            delta,
            "run",
            return_value=CompletedProcess(
                args=["sha256sum", str(self.image)],
                returncode=0,
                stdout=f"{digest}  {self.image}\n",
                stderr="",
            ),
        ):
            self.assertEqual(delta.verify_image(self.image), digest)

    def test_verify_image_rejeita_hash_que_nao_confere(self) -> None:
        sidecar = Path(str(self.image) + ".sha256")
        sidecar.write_text(f"{'0' * 64}  {self.image.name}\n", encoding="utf-8")
        with patch.object(delta, "require_tool"), patch.object(
            delta,
            "run",
            return_value=CompletedProcess(
                args=["sha256sum", str(self.image)],
                returncode=0,
                stdout=f"{'1' * 64}  {self.image}\n",
                stderr="",
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "SHA256_da_imagem_nao_confere"):
                delta.verify_image(self.image)

    def test_verify_image_rejeita_sidecar_de_outra_imagem(self) -> None:
        sidecar = Path(str(self.image) + ".sha256")
        sidecar.write_text(f"{'a' * 64}  outra-imagem.img\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "checksum_nao_corresponde"):
            delta.verify_image(self.image)

    def test_chave_publica_com_multiplas_linhas_e_rejeitada_sem_ssh_keygen(self) -> None:
        self.key.write_text(
            "ssh-ed25519 AAAATESTKEYDATA\nssh-ed25519 SEGUNDA-CHAVE\n",
            encoding="utf-8",
        )
        with patch.object(delta, "require_tool") as require_tool:
            with self.assertRaisesRegex(RuntimeError, "exatamente_uma_chave"):
                delta.find_ssh_key(str(self.key))
        require_tool.assert_not_called()


    def test_diagnostico_separa_dominio_ausente_de_erro_de_conexao(self) -> None:
        diagnostic = ROOT / "deploy" / "delta" / "diagnosticar_vm_mvp0.sh"
        for mode, expected_state in (
            ("unknown", "DOMAIN_EXISTS=unknown"),
            ("absent", "DOMAIN_EXISTS=no"),
            ("present", "DOMAIN_EXISTS=yes"),
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="delta-diagnostic-") as temp:
                root = Path(temp)
                home = root / "home"
                home.mkdir()
                bin_dir = root / "bin"
                bin_dir.mkdir()
                current_storage = root / "configured-storage"
                current_storage.mkdir()
                storage_root = root / "libvirt-images"
                dedicated_storage = storage_root / "delta-mvp0-storage"
                dedicated_storage.mkdir(parents=True)
                legacy_storage = home / "NyxOS" / "VPS"
                legacy_storage.mkdir(parents=True)
                leftover = dedicated_storage / "delta-mvp0.qcow2"
                leftover.write_bytes(b"fixture marker, not a real disk")

                fake_virsh = bin_dir / "virsh"
                fake_virsh.write_text(
                    """#!/usr/bin/env bash
set -u
case "$*" in
  *" dominfo "*)
    if [[ "$NYXOS_TEST_VIRSH_MODE" == "present" ]]; then
      printf 'Name: delta-mvp0\\nState: shut off\\n'
      exit 0
    fi
    printf 'libvirt connection unavailable\\n' >&2
    exit 1
    ;;
  *" list --all --name")
    case "$NYXOS_TEST_VIRSH_MODE" in
      unknown) printf 'libvirt connection unavailable\\n' >&2; exit 1 ;;
      absent) printf 'other-vm\\n'; exit 0 ;;
      present) printf 'delta-mvp0\\n'; exit 0 ;;
    esac
    ;;
  *" pool-info "*) exit 1 ;;
  *" pool-list --all"*) printf 'Name State Autostart\\ndefault active yes\\n'; exit 0 ;;
  *" list --all"*) printf ' Id Name State\\n -  other-vm shut off\\n'; exit 0 ;;
  *) exit 0 ;;
esac
""",
                    encoding="utf-8",
                )
                fake_virsh.chmod(0o755)

                env = os.environ.copy()
                env.update({
                    "HOME": str(home),
                    "PATH": str(bin_dir) + os.pathsep + env.get("PATH", ""),
                    "NYXOS_DELTA_VM_STORAGE": str(current_storage),
                    "NYXOS_DELTA_STORAGE_ROOT": str(storage_root),
                    "NYXOS_DELTA_VM_NAME": "delta-mvp0",
                    "NYXOS_TEST_VIRSH_MODE": mode,
                })
                completed = subprocess.run(
                    ["bash", str(diagnostic)],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn(expected_state, completed.stdout)
                self.assertIn(str(dedicated_storage), completed.stdout)
                self.assertIn(str(legacy_storage), completed.stdout)
                self.assertIn("delta-mvp0.qcow2", completed.stdout)
                if mode == "unknown":
                    self.assertIn("Não crie outra VM nem remova artefatos", completed.stdout)
                    self.assertNotIn("DOMAIN_EXISTS=no", completed.stdout)
                elif mode == "absent":
                    self.assertIn("ausência foi confirmada", completed.stdout)
                else:
                    self.assertIn("Name: delta-mvp0", completed.stdout)
                self.assertTrue(leftover.is_file(), "o diagnóstico não pode alterar arquivos existentes")

    def test_diagnostico_permanece_somente_leitura_e_cobre_storage_dedicado(self) -> None:
        diagnostic = (ROOT / "deploy" / "delta" / "diagnosticar_vm_mvp0.sh").read_text(encoding="utf-8")
        self.assertIn('DOMAIN_EXISTS="unknown"', diagnostic)
        self.assertIn('virsh -c qemu:///system list --all --name', diagnostic)
        self.assertIn('NYXOS_DELTA_VM_STORAGE', diagnostic)
        self.assertIn('delta-mvp0-storage', diagnostic)
        self.assertIn('LEGACY_STORAGE="${HOME}/NyxOS/VPS"', diagnostic)
        for forbidden in ("virsh destroy", "virsh undefine", "rm -rf", "chmod 777", "systemctl start"):
            self.assertNotIn(forbidden, diagnostic)

if __name__ == "__main__":
    unittest.main(verbosity=2)
