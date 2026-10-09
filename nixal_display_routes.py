#!/usr/bin/env python3
"""Resolução segura das rotas HTTP do bundle estático Nyxal Display."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlsplit


def resolve_display_file(root: Path | str, request_target: str) -> Path | None:
    """Resolve /display/* para um arquivo real do bundle, com fallback SPA seguro."""
    try:
        request_path = unquote(urlsplit(request_target).path)
    except (TypeError, ValueError):
        return None

    if request_path == "/display" or request_path == "/display/":
        relative = "index.html"
    elif request_path.startswith("/display/"):
        relative = request_path.removeprefix("/display/").lstrip("/")
        relative = relative or "index.html"
    else:
        return None

    root_path = Path(root).resolve()
    candidate = (root_path / relative).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        return None

    if candidate.is_file():
        return candidate

    # Rotas internas do desktop são tratadas pelo router SPA. Arquivos com
    # extensão (JS/CSS/imagens) que não existem continuam retornando 404.
    if not Path(relative).suffix:
        index = (root_path / "index.html").resolve()
        try:
            index.relative_to(root_path)
        except ValueError:
            return None
        if index.is_file():
            return index

    return None


__all__ = ["resolve_display_file"]
