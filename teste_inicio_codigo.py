#!/usr/bin/env python3
"""Regressões da interface única do NyxOS e de seus launchers."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    interface_path = ROOT / "interface" / "index.html"
    assert interface_path.is_file(), "interface principal ausente"
    interface = interface_path.read_text(encoding="utf-8")

    # Uma única implementação visual, com voz como modo da mesma página.
    assert interface.count('id="nyxalAvatar"') == 1
    assert 'id="nyxalCharacterSvg"' in interface
    assert "nyxal-lunar-sigil" in interface
    assert 'get("modo") === "voz"' in interface
    assert "/interface/js/nyxal-voice-console.js" in interface
    assert "/interface/js/nyxal-api-client.js" in interface

    removidos = (
        "interface/index-legacy.html",
        "interface/nyxos-panel.html",
        "interface/startup.html",
        "interface/display",
        "nixal_display_routes.py",
        "teste_nixal_display_routes.py",
        "deploy/display",
    )
    for relativo in removidos:
        assert not (ROOT / relativo).exists(), f"interface duplicada ainda existe: {relativo}"

    api = (ROOT / "nyxal_web_api.py").read_text(encoding="utf-8")
    assert 'if parsed_path == "/":' in api
    assert 'caminho = caminho_interface("index.html")' in api
    assert "caminho_display" not in api
    assert "resolve_display_file" not in api
    assert "self.send_response(308)" in api
    for alias in (
        "/display",
        "/interface/index-legacy.html",
        "/interface/nyxos-panel.html",
        "/interface/startup.html",
    ):
        assert alias in api, f"alias antigo sem redirecionamento: {alias}"

    for relativo in (
        "deploy/systemd/iniciar_nyxos_shell.sh",
        "deploy/systemd/iniciar_nyxos_interface.sh",
    ):
        launcher = (ROOT / relativo).read_text(encoding="utf-8")
        assert 'http://127.0.0.1:8010/' in launcher
        assert "startup.html" not in launcher
        assert "file://" not in launcher
        assert "modo=voz" not in launcher

    shell = (ROOT / "deploy" / "systemd" / "iniciar_nyxos_shell.sh").read_text(encoding="utf-8")
    assert "--kiosk" not in shell
    assert "--new-window" in shell
    assert "--autoplay-policy=no-user-gesture-required" in shell

    installer = (ROOT / "deploy" / "systemd" / "instalar_nyxos_servicos.sh").read_text(encoding="utf-8")
    assert "preparar_nyxos_display" not in installer
    assert "npm install" not in installer

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

    for marcador_sessao in (
        'const sessaoMorta = [',
        '"sessao_nao_valida",',
        '"sessao_inativa",',
        "nyxalSessionId = null;",
        'sessionStorage.removeItem("NYXAL_SESSION_ID");',
    ):
        assert marcador_sessao in interface, (
            f"interface perdeu a recuperação de sessão após reinício: {marcador_sessao}"
        )

    assert "cancelAnimationFrame(voiceVadFrame)" not in interface
    assert "cancelAnimationFrame(voiceBargeInFrame)" not in interface

    print("NYXOS_SINGLE_INTERFACE_OK")
    print("NYXOS_VOICE_MODE_SAME_PAGE_OK")
    print("NYXOS_LEGACY_URL_REDIRECTS_OK")
    print("NYXOS_PERFORMANCE_AND_SESSION_GUARDS_OK")


if __name__ == "__main__":
    main()
