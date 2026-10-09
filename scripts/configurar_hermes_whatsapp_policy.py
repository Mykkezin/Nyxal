#!/usr/bin/env python3
"""Define a política de DMs não autorizados do WhatsApp como ignore, preservando o restante YAML."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

CONFIG = Path.home() / ".hermes" / "config.yaml"


def apply_policy() -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    lines = CONFIG.read_text(encoding="utf-8").splitlines() if CONFIG.exists() else []
    start = next((i for i, line in enumerate(lines) if line.strip() == "whatsapp:" and not line.startswith((" ", "\t"))), None)

    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["whatsapp:", "  unauthorized_dm_behavior: ignore"])
    else:
        end = len(lines)
        for i in range(start + 1, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith((" ", "\t", "#")):
                end = i
                break
        target = None
        for i in range(start + 1, end):
            line = lines[i]
            if line.startswith(("  ", "\t")) and line.strip().startswith("unauthorized_dm_behavior:"):
                target = i
                break
        if target is None:
            lines.insert(start + 1, "  unauthorized_dm_behavior: ignore")
        else:
            lines[target] = "  unauthorized_dm_behavior: ignore"

    text = "\n".join(lines).rstrip() + "\n"
    CONFIG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="config.yaml.", dir=str(CONFIG.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.chmod(temporary, 0o600)
        os.replace(temporary, CONFIG)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    apply_policy()
    print(f"Política aplicada em {CONFIG}: DMs não autorizadas serão ignoradas.")
