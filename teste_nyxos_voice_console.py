#!/usr/bin/env python3
"""Regressão estática para os recursos da consola residente de voz."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class TestNyxalVoiceConsole(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "interface" / "index.html").read_text(encoding="utf-8")
        cls.console = (ROOT / "interface" / "js" / "nyxal-voice-console.js").read_text(encoding="utf-8")
        cls.api = (ROOT / "nyxal_web_api.py").read_text(encoding="utf-8")
        cls.telemetry = (ROOT / "nixal_observabilidade_sistema.py").read_text(encoding="utf-8")

    def test_voice_console_is_loaded(self):
        self.assertIn('/interface/js/nyxal-voice-console.js', self.html)
        self.assertIn('modo=voz', self.html)

    def test_console_uses_existing_real_telemetry(self):
        self.assertIn('"/api/agent/contexto"', self.console)
        self.assertIn('"/api/public/status"', self.console)
        self.assertIn('if parsed_path == "/api/agent/contexto":', self.api)
        for metric in ('"memoria"', '"armazenamento_home"', '"temperaturas"', '"gpu"'):
            self.assertIn(metric, self.telemetry)

    def test_vps_tools_use_existing_api_and_safe_actions(self):
        self.assertIn('"/api/vps/status"', self.console)
        self.assertIn('"/api/vps/instances"', self.console)
        self.assertIn('"/api/vps/action"', self.console)
        self.assertIn('["start", "shutdown", "reboot"]', self.console)
        self.assertNotIn('["destroy"', self.console)

    def test_image_generation_uses_existing_visual_endpoint(self):
        self.assertIn('"/api/agent/image"', self.console)
        self.assertIn("nyxalHandleImageIntent", self.console)
        self.assertIn("window.nyxalHandleImageIntent", self.html)
        self.assertIn('payload.imagem_base64', self.console)
        self.assertIn('payload.mime_type', self.console)

    def test_weather_reflections_and_keyboard_shortcuts_are_present(self):
        self.assertIn('api.open-meteo.com/v1/forecast', self.console)
        self.assertIn('3 * 60 * 60 * 1000', self.console)
        self.assertIn('event.code === "Space"', self.console)
        for mode in ('cyber', 'data', 'image', 'reflection'):
            self.assertIn('"' + mode + '"', self.console)


if __name__ == "__main__":
    unittest.main()
