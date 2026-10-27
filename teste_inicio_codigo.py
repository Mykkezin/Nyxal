#!/usr/bin/env python3
"""Regressões para a inicialização NyxOS totalmente renderizada por código."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    splash_path = ROOT / "interface" / "startup.html"
    assert splash_path.is_file(), "interface/startup.html ausente"
    splash = splash_path.read_text(encoding="utf-8").lower()
    video_path = ROOT / "interface" / "assets" / "nyxos-startup.mp4"
    assert not video_path.exists(), "o vídeo de inicialização foi reintroduzido"

    # A animação deve ser autônoma: nada de vídeo, fontes ou bibliotecas remotas.
    assert "<video" not in splash
    assert ".mp4" not in splash
    assert "<script src=" not in splash
    assert "https://" not in splash
    assert "prefers-reduced-motion: reduce" in splash
    assert "location.replace(next)" in splash
    assert "new url(requestednext)" in splash
    assert 'destination.protocol === "http:"' in splash
    assert 'destination.protocol === "https:"' in splash
    assert 'const allowedhosts = new set(["127.0.0.1", "localhost", "[::1]", "::1"])' in splash
    assert "allowedhosts.has(destination.hostname.tolowercase())" in splash
    assert 'const endpointportallowed = destination.port === "8010"' in splash
    splash_compact = " ".join(splash.split())
    assert "hostallowed && endpointportallowed && pathallowed && noextracomponents &&" in splash_compact
    assert 'destination.pathname === "/" || destination.pathname === "/index.html"' in splash
    assert "pathallowed &&" in splash
    assert "noextracomponents &&" in splash_compact
    assert "destination.search" in splash
    assert "destination.hash" in splash
    assert "destination.username" in splash
    assert "destination.password" in splash
    assert "fallbacknext" in splash
    assert 'id="progress"' in splash
    assert 'id="stars"' in splash

    for nome in (
        "deploy/systemd/iniciar_nyxos_shell.sh",
        "deploy/systemd/iniciar_nyxos_interface.sh",
    ):
        script = (ROOT / nome).read_text(encoding="utf-8")
        assert "startup.html" in script, f"{nome} não usa a animação em código"
        assert ".mp4" not in script, f"{nome} ainda depende do vídeo"
        assert "mpv" not in script, f"{nome} ainda invoca mpv"

    # Regressões de desempenho e clareza do estado operacional da interface.
    interface = (ROOT / "interface" / "index.html").read_text(encoding="utf-8")
    for marcador in (
        "const NYXAL_VOICE_SAMPLE_INTERVAL_MS = 40;",
        "window.setTimeout(runContinuousVoiceVad, NYXAL_VOICE_SAMPLE_INTERVAL_MS)",
        "window.setTimeout(runVoiceBargeInMonitor, NYXAL_VOICE_SAMPLE_INTERVAL_MS)",
        "renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25));",
        "window.setTimeout(animate, 33);",
        "window.setTimeout(drawBg, 50);",
        "nyxalVoiceBackendStatus",
        "updateNyxalVoiceBackendStatus(data, true);",
        "updateNyxalVoiceBackendStatus(null, false);",
        "setInterval(fetchNyxosOperationalContext, 30000);",
    ):
        assert marcador in interface, f"otimização da interface ausente: {marcador}"

    assert "cancelAnimationFrame(voiceVadFrame)" not in interface
    assert "cancelAnimationFrame(voiceBargeInFrame)" not in interface

    # O shell residente não deve forçar a miniatura de voz nem ocupar a tela em modo kiosk.
    shell = (ROOT / "deploy" / "systemd" / "iniciar_nyxos_shell.sh").read_text(encoding="utf-8")
    assert 'INTERFACE_URL="${NYXOS_INTERFACE_URL:-http://127.0.0.1:8010/}"' in shell
    assert "--kiosk" not in shell, "o shell não deve forçar o modo tela cheia"
    assert "--new-window" in shell, "a interface deve abrir em janela normal"

    print("NYXOS_STARTUP_CODE_ONLY_OK")
    print("NYXOS_STARTUP_NO_EXTERNAL_ASSETS_OK")
    print("NYXOS_STARTUP_REDUCED_MOTION_OK")
    print("NYXOS_SHELL_WINDOWED_NO_VOICE_MINIATURE_OK")


if __name__ == "__main__":
    main()
