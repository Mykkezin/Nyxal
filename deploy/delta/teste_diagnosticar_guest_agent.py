#!/usr/bin/env python3
"""Mocked, read-only regressions for the DELTA guest-agent host diagnostic."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("diagnosticar_vm_mvp0.sh")


class GuestAgentDiagnosticTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "virsh.log"
        fake = self.bin / "virsh"
        fake.write_text(
            """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$FAKE_VIRSH_LOG"
if [[ "$1" == "-c" ]]; then shift 2; fi
operation="$1"
shift
case "$operation" in
  dominfo)
    [[ "$FAKE_DOMAIN_EXISTS" == "yes" ]] || exit 1
    printf 'Name: %s\\n' "$1"
    ;;
  dumpxml)
    [[ "$FAKE_DUMPXML_OK" == "yes" ]] || exit 1
    if [[ "$FAKE_CHANNEL" == "present" ]]; then
      cat <<'XML'
<domain><devices><channel type="unix"><target type="virtio" name="org.qemu.guest_agent.0" /></channel></devices></domain>
XML
    else
      cat <<'XML'
<domain><devices><console type="pty" /></devices></domain>
XML
    fi
    ;;
  domblklist) printf 'Type Device Target Source\\n' ;;
  domstate) printf 'running\\n' ;;
  list)
    [[ "$FAKE_LIST_OK" == "yes" ]] || exit 1
    if [[ "$1" == "--all" && "$2" == "--name" ]]; then
      [[ "$FAKE_DOMAIN_EXISTS" == "yes" ]] && printf 'delta-mvp0\\n'
    else
      printf ' Id Name State\\n'
    fi
    ;;
  pool-info) exit 1 ;;
  qemu-agent-command)
    [[ "$FAKE_AGENT_PING" == "success" ]] || exit 1
    printf '{"return":{}}\\n'
    ;;
  *) exit 1 ;;
esac
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)

    def run_diagnostic(self, **overrides: str) -> tuple[subprocess.CompletedProcess[str], str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": str(self.bin) + os.pathsep + env.get("PATH", ""),
                "HOME": str(self.root / "home"),
                "NYXOS_DELTA_VM_NAME": "delta-mvp0",
                "NYXOS_VPS_STORAGE": str(self.root / "legacy-storage"),
                "NYXOS_DELTA_STORAGE_ROOT": str(self.root / "system-storage"),
                "FAKE_VIRSH_LOG": str(self.log),
                "FAKE_DOMAIN_EXISTS": "yes",
                "FAKE_LIST_OK": "yes",
                "FAKE_DUMPXML_OK": "yes",
                "FAKE_CHANNEL": "present",
                "FAKE_AGENT_PING": "success",
            }
        )
        (self.root / "home").mkdir(exist_ok=True)
        env.update(overrides)
        result = subprocess.run(
            [shutil.which("bash") or "bash", str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            check=False,
        )
        log = self.log.read_text(encoding="utf-8") if self.log.exists() else ""
        return result, log

    def test_present_channel_and_guest_ping_success_are_reported(self) -> None:
        result, log = self.run_diagnostic(
            FAKE_CHANNEL="present",
            FAKE_AGENT_PING="success",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GUEST_AGENT_CHANNEL=present", result.stdout)
        self.assertIn("GUEST_AGENT_PING=success", result.stdout)
        self.assertIn("qemu-agent-command", log)
        self.assertIn("guest-ping", log)

    def test_missing_channel_does_not_send_agent_command(self) -> None:
        result, log = self.run_diagnostic(FAKE_CHANNEL="absent")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GUEST_AGENT_CHANNEL=absent", result.stdout)
        self.assertIn("GUEST_AGENT_PING=not_attempted", result.stdout)
        self.assertNotIn("qemu-agent-command", log)

    def test_unresponsive_agent_is_reported_without_restart(self) -> None:
        result, log = self.run_diagnostic(
            FAKE_CHANNEL="present",
            FAKE_AGENT_PING="fail",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GUEST_AGENT_CHANNEL=present", result.stdout)
        self.assertIn("GUEST_AGENT_PING=failed", result.stdout)
        self.assertNotIn("systemctl", log)
        self.assertNotIn("destroy", log)

    def test_uncertain_domain_state_never_probes_guest(self) -> None:
        result, log = self.run_diagnostic(
            FAKE_DOMAIN_EXISTS="no",
            FAKE_LIST_OK="no",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DOMAIN_EXISTS=unknown", result.stdout)
        self.assertIn("GUEST_AGENT_CHANNEL=unknown", result.stdout)
        self.assertIn("GUEST_AGENT_PING=not_attempted", result.stdout)
        self.assertNotIn("qemu-agent-command", log)


if __name__ == "__main__":
    unittest.main()
