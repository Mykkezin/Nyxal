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
        self.assertIn('get("modo") === "voz"', self.html)
        self.assertIn('document.getElementById("nyxalVoiceSurface")', self.console)
        self.assertIn("new MutationObserver", self.console)
        self.assertIn("setInterval(tickClock, 1000)", self.console)

    def test_autonomous_avatar_replaces_video_and_intercepts_image_requests(self):
        self.assertIn('id="nyxalCharacterSvg"', self.html)
        self.assertNotIn("<video", self.html.lower())
        self.assertNotIn('id="nyxalVideoUpload"', self.html)
        image_handler = self.html.index("window.nyxalHandleImageIntent(msg)")
        chat_request = self.html.index("nyxalApiPost('/api/chat'", image_handler)
        self.assertLess(image_handler, chat_request)

    def test_chat_surfaces_http_errors_and_recovers_sessions_instead_of_reporting_connection_failure(self):
        client = (ROOT / "interface" / "js" / "nyxal-api-client.js").read_text(encoding="utf-8")
        self.assertIn("throwOnError = true", client)
        self.assertIn("if (!response.ok && throwOnError)", client)
        chat_call = self.html.index("nyxalApiPost('/api/chat'")
        recovery = self.html.index("sessaoConversacionalRecuperavel(data)", chat_call)
        catch_block = self.html.index("Chat API fetch error:", recovery)
        self.assertIn("throwOnError: false", self.html[chat_call:recovery])
        self.assertLess(recovery, catch_block)

    def test_voice_only_screen_has_a_prominent_holographic_face_and_clean_control_card(self):
        # Keep the top HUD understated while improving the centrepiece and microphone panel.
        self.assertIn('nyxal-voice-control-card', self.html)
        self.assertIn('nyxal-voice-face-frame', self.html)
        self.assertIn('nyxal-voice-scanline', self.html)
        self.assertIn('nyxalFaceDataClip', self.html)
        self.assertIn('nyxal-face-data-line', self.html)
        self.assertIn('max-height: 52vh', self.html)
        self.assertIn('status.dataset.state', self.html)
        self.assertIn('font-size:12px', self.console)
        self.assertIn('min-height:32px', self.console)
        self.assertIn('rgba(145,190,225,.28)', self.console)

    def test_immersive_hologram_has_large_centerpiece_and_spatial_signal_panels(self):
        self.assertIn('viewBox="48 0 264 320"', self.html)
        self.assertIn('nyxal-voice-sidepanel-left', self.html)
        self.assertIn('nyxal-voice-sidepanel-right', self.html)
        self.assertIn('nyxalSideSignal', self.html)
        self.assertIn('nyxalCorePulse', self.html)
        self.assertIn('grid-template-columns: minmax(210px,1fr) minmax(460px,620px) minmax(210px,1fr)', self.html)
        self.assertIn('max-height: 64vh', self.html)
        self.assertIn('nyxalVoiceOuterOrbit', self.html)
        self.assertIn('nyxalVoiceScanSweep', self.html)

    def test_side_panels_follow_real_microphone_rms_and_voice_lifecycle(self):
        self.assertIn("sideRms.textContent = sampleAvailable ? voiceRmsAtual.toFixed(3) : '—'", self.html)
        self.assertIn("sideSignal.dataset.active = String(Boolean(sampleAvailable && voiceConversationActive && !voiceConversationBusy))", self.html)
        self.assertIn("function updateNyxalHologramPanels(state)", self.html)
        self.assertIn("updateNyxalHologramPanels(state)", self.html)
        self.assertIn("data-nyxal-step", self.html)
        self.assertIn("state === 'processing'", self.html)
        self.assertIn("state === 'speaking'", self.html)
        self.assertIn("stage.style.setProperty('--voice-glow'", self.html)
        self.assertIn("stage.style.setProperty('--voice-bloom'", self.html)
        self.assertIn("var(--voice-glow,.45)", self.html)
        self.assertIn('.nyxal-side-dot[data-state="active"]', self.html)

    def test_system_hud_has_readable_metrics_without_becoming_the_centerpiece(self):
        self.assertIn('font-size:12px;letter-spacing:.035em', self.console)
        self.assertIn('min-height:32px;padding:6px 11px', self.console)
        self.assertIn('position:absolute;top:15px;left:18px;right:18px', self.console)
        self.assertIn('@media(max-width:720px)', self.console)
        self.assertIn('prefers-reduced-motion: reduce', self.html)

    def test_console_uses_existing_real_telemetry(self):
        self.assertIn('"/api/agent/contexto"', self.console)
        self.assertIn('"/api/public/status"', self.console)
        self.assertIn('if parsed_path == "/api/agent/contexto":', self.api)
        for metric in ('"memoria"', '"armazenamento_home"', '"temperaturas"', '"gpu"'):
            self.assertIn(metric, self.telemetry)
        # Uma fonte de telemetria pode falhar sem impedir a outra; leituras ausentes
        # aparecem como indisponíveis, não como zero nem como dados antigos.
        self.assertIn("function fetchSnapshot(path, label)", self.console)
        self.assertIn("return {};", self.console)
        self.assertIn('node.textContent = value !== null && value !== undefined && Number.isFinite(number)', self.console)

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
        self.assertIn('["image/png", "image/jpeg", "image/webp"]', self.console)
        self.assertIn("24 * 1024 * 1024", self.console)
        self.assertIn('replace(/\\s+/g, "")', self.console)
        self.assertIn('window.nyxalApiPost("/api/agent/image"', self.console)
        self.assertIn('/interface/js/nyxal-api-client.js', self.html)

    def test_chat_image_is_rendered_in_the_main_display_without_voice_console(self):
        self.assertIn("function showImageInMainDisplay(imageUrl, prompt, filename)", self.console)
        self.assertIn('var mainDisplayImage = !output;', self.console)
        self.assertIn('id = "nyxalGeneratedImageDialog"', self.console)
        self.assertIn('if (document.getElementById("nyxalVoiceConsole"))', self.console)

    def test_weather_reflections_and_keyboard_shortcuts_are_present(self):
        self.assertIn('api.open-meteo.com/v1/forecast', self.console)
        self.assertIn('3 * 60 * 1000', self.console)
        self.assertIn('event.code === "Space"', self.console)
        for mode in ('cyber', 'reverse', 'data', 'image', 'reflection'):
            self.assertIn('"' + mode + '"', self.console)

    def test_reverse_engineering_has_explicit_ui_entry_and_scope(self):
        self.assertIn('data-nvc-view="reverse"', self.console)
        self.assertIn('id="nvcReverseStart"', self.console)
        self.assertIn("startReverseEngineeringMode", self.console)
        self.assertIn("ambiente isolado", self.console)
        self.assertIn('"7": "reverse"', self.console)

    def test_metrics_sources_fail_independently_and_gpu_temperature_has_fallback(self):
        self.assertIn("function fetchSnapshot(path, label)", self.console)
        self.assertIn('fetchSnapshot("/api/agent/contexto", "observabilidade")', self.console)
        self.assertIn('fetchSnapshot("/api/public/status", "estado público")', self.console)
        self.assertIn("Array.isArray(resources.gpu)", self.console)
        self.assertIn("gpu.temperatura_c", self.console)

    def test_main_dashboard_restores_weather_and_gpu_temperature_metrics(self):
        self.assertIn('id="gpuUsageText"', self.html)
        self.assertIn('id="systemTempText"', self.html)
        self.assertIn('function fetchNyxalObservability()', self.html)
        self.assertIn('fetch(window.NYXAL_API_BASE + "/api/agent/contexto"', self.html)
        self.assertIn('function atualizarClima()', self.html)
        self.assertIn('api.open-meteo.com/v1/forecast', self.html)
        self.assertIn('id="weatherIcon"', self.html)
        self.assertIn("icone.className", self.html)
        self.assertIn('window.setInterval(atualizarClima, 10 * 60 * 1000)', self.html)
        self.assertIn('window.setInterval(fetchNyxalObservability, 15000)', self.html)

    def test_weather_failure_clears_stale_measurements(self):
        climate = self.html[self.html.index("async function atualizarClima()"):self.html.index("function desenharGraficoSistema()", self.html.index("async function atualizarClima()"))]
        catch_block = climate[climate.index("} catch (erro) {"):]
        for name in ("temperatura", "sensacao", "umidade", "vento"):
            self.assertIn(name + '.innerText = "—";', catch_block)
        self.assertIn('condicao.innerText = "Clima indisponível";', catch_block)

    def test_music_widget_opens_spotify_safely_without_faking_playback(self):
        self.assertIn('id="spotifyStatus"', self.html)
        self.assertIn('aria-label="Abrir Spotify Web"', self.html)
        start = self.html.index("function togglePlayMusic()")
        end = self.html.index("function addNewEventPrompt()", start)
        music = self.html[start:end]
        self.assertIn("window.open('about:blank', '_blank')", music)
        self.assertIn("popup.opener = null", music)
        self.assertIn("popup.location.replace('https://open.spotify.com/')", music)
        self.assertIn("window.__nyxosSpotifyWindow", music)
        self.assertIn("Pop-up bloqueado", music)
        self.assertIn("'BLOQUEADO'", music)
        self.assertNotIn("Reprodução iniciada", music)

    def test_infinity_drag_handles_cancel_resize_storage_and_viewport_bounds(self):
        self.assertIn("z-index: 9999 !important", self.html)
        start = self.html.index("function initInfinityDrag()")
        end = self.html.index("function toggleInfinityHub()", start)
        drag = self.html[start:end]
        self.assertIn("document.body.appendChild(hub)", drag)
        self.assertIn("core.style.touchAction = 'none'", drag)
        self.assertIn("core.addEventListener('pointercancel', finishDrag)", drag)
        self.assertIn("core.addEventListener('lostpointercapture'", drag)
        self.assertIn("window.addEventListener('resize'", drag)
        self.assertIn("function clampCoordinate(value, viewportSize)", drag)
        self.assertIn("sessionStorage.setItem(STORAGE_KEY", drag)
        self.assertIn("passive: false", drag)
        self.assertIn("core.dataset.dragSuppressed", drag)

    def test_main_dashboard_rotates_reflections_every_three_minutes(self):
        self.assertIn('function rotacionarReflexao()', self.html)
        self.assertIn('window.setInterval(rotacionarReflexao, 3 * 60 * 1000)', self.html)

    def test_reflections_rotate_after_three_minutes_and_are_dismissible(self):
        self.assertIn("3 * 60 * 1000", self.console)
        self.assertIn("function checkReflectionInterval()", self.console)
        self.assertIn("rotateReflection(true)", self.console)
        self.assertIn("nvcReflectionDismiss", self.console)


if __name__ == "__main__":
    unittest.main()
