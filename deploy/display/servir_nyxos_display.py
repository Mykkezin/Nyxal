#!/usr/bin/env python3
"""Servidor local do build estático do Nyxal-Display."""

from __future__ import annotations

import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(
    os.environ.get(
        "NYXOS_DISPLAY_DIR",
        str(Path.home() / "Nyxal-Display" / "dist"),
    )
).resolve()
HOST = os.environ.get("NYXOS_DISPLAY_HOST", "127.0.0.1")
PORT = int(os.environ.get("NYXOS_DISPLAY_PORT", "3000"))

class DisplayHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        requested = self.translate_path(self.path)
        if not Path(requested).is_file():
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, format_string: str, *args) -> None:
        print("[NyxOS-Display]", format_string % args)

def main() -> None:
    if not (ROOT / "index.html").is_file():
        raise SystemExit(f"build do Nyxal-Display não encontrado: {ROOT / 'index.html'}")
    server = ThreadingHTTPServer((HOST, PORT), DisplayHandler)
    print(f"[NyxOS-Display] servindo {ROOT}")
    print(f"[NyxOS-Display] escutando em http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
