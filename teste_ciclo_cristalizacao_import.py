#!/usr/bin/env python3
"""Regression test: importing ciclo_cristalizacao must be side-effect-free."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> None:
    repo_root = Path(__file__).resolve().parent

    with tempfile.TemporaryDirectory(prefix="nyxal-cristal-import-") as temp_dir:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            value
            for value in (str(repo_root), env.get("PYTHONPATH", ""))
            if value
        )
        script = (
            "import sys\n"
            "import ciclo_cristalizacao\n"
            "assert 'ollama' not in sys.modules, "
            "'Ollama must not be imported just by importing the module'\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=temp_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        assert result.returncode == 0, (
            "Import failed or imported Ollama unexpectedly.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert result.stdout == "", (
            f"Import unexpectedly printed to stdout: {result.stdout!r}"
        )
        assert result.stderr == "", (
            f"Import unexpectedly printed to stderr: {result.stderr!r}"
        )
        leftovers = list(Path(temp_dir).iterdir())
        assert not leftovers, (
            "Import created filesystem artifacts: "
            + ", ".join(item.name for item in leftovers)
        )

    print("OK: import is silent, dependency-lazy, and filesystem-side-effect-free")


if __name__ == "__main__":
    main()
