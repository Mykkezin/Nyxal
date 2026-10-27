#!/usr/bin/env python3
"""Offline tests for Nyxal's contextual voice profile and speech text shaping."""

import unittest

from nyxal_voice_prosody import (
    choose_speech_profile,
    clean_speech_text,
    prepare_spoken_reply,
)


class VoiceProsodyTests(unittest.TestCase):
    def test_distress_and_empathy_slow_gently(self):
        profile = choose_speech_profile(
            "Estou muito triste hoje.", "Sinto muito. Estou aqui com você.", 1.0
        )
        self.assertEqual(profile.style, "gentle")
        self.assertAlmostEqual(profile.speed, 0.94)

    def test_safety_instructions_are_measured_not_excited(self):
        profile = choose_speech_profile(
            "Tem fumaça saindo do aparelho.",
            "Atenção: afaste-se do local e ligue para a emergência.",
            1.0,
        )
        self.assertEqual(profile.style, "focused")
        self.assertAlmostEqual(profile.speed, 0.97)
        self.assertFalse(profile.conversational)

    def test_success_can_be_a_little_brighter(self):
        profile = choose_speech_profile(
            "Consegui passar na prova!", "Parabéns, você conseguiu!", 1.0
        )
        self.assertEqual(profile.style, "upbeat")
        self.assertAlmostEqual(profile.speed, 1.04)

    def test_user_in_a_hurry_gets_a_brisk_but_not_extreme_delivery(self):
        profile = choose_speech_profile(
            "Estou com pressa, vai direto ao ponto.",
            "A reunião começa em cinco minutos.",
            1.0,
        )
        self.assertEqual(profile.style, "brisk")
        self.assertAlmostEqual(profile.speed, 1.08)

    def test_distress_context_is_gentle_even_without_fixed_empathy_phrase(self):
        profile = choose_speech_profile(
            "Estou triste hoje.",
            "Vamos organizar isso com calma.",
            1.0,
        )
        self.assertEqual(profile.style, "gentle")
        self.assertAlmostEqual(profile.speed, 0.94)

    def test_question_style_is_not_overacted(self):
        profile = choose_speech_profile(
            "Pode me ajudar?", "Quer que eu explique de outro jeito?", 1.0
        )
        self.assertEqual(profile.style, "curious")
        self.assertAlmostEqual(profile.speed, 0.98)

    def test_speed_is_clamped_and_bad_base_is_safe(self):
        self.assertEqual(choose_speech_profile("", "Olá.", 999).speed, 1.25)
        self.assertEqual(choose_speech_profile("", "Olá.", "bad").speed, 1.0)

    def test_markdown_headings_and_lists_get_a_pause_boundary(self):
        self.assertEqual(
            clean_speech_text("## Status\n- Voz **feminina** ativada."),
            "Status. Voz feminina ativada.",
        )
        self.assertEqual(
            clean_speech_text("## Status!\n- Já está pronto."),
            "Status! Já está pronto.",
        )
        self.assertEqual(
            clean_speech_text("1. Primeiro item.\n2. Segundo item!"),
            "Primeiro item. Segundo item!",
        )

    def test_intentional_ellipses_are_preserved_as_pause_cues(self):
        self.assertEqual(
            clean_speech_text("Então... deixa eu ver"),
            "Então... deixa eu ver.",
        )
        self.assertEqual(
            clean_speech_text("Pausa........ e continuo."),
            "Pausa... e continuo.",
        )

    def test_code_is_not_read_character_by_character(self):
        code_tick = chr(96)
        self.assertEqual(
            clean_speech_text("Execute " + code_tick + "print(1)" + code_tick + " e confira."),
            "Execute print(1) e confira.",
        )
        self.assertIn(
            "Omiti um bloco de código",
            clean_speech_text(chr(96) * 3 + "py\nprint(1)\n" + chr(96) * 3),
        )

    def test_contractions_only_when_conversation_is_informal(self):
        informal = choose_speech_profile("Oi, tá tudo bem?", "Está tudo bem, para você.")
        self.assertTrue(informal.conversational)
        self.assertEqual(
            prepare_spoken_reply("Está tudo bem, para você.", "Oi, tá tudo bem?", informal),
            "Tá tudo bem, pra você.",
        )
        formal = choose_speech_profile("Preciso de uma análise técnica.", "O serviço está ativo.")
        self.assertFalse(formal.conversational)
        self.assertEqual(
            prepare_spoken_reply("O serviço está ativo.", "", formal),
            "O serviço está ativo.",
        )

    def test_no_fake_fillers_or_breaths_are_added(self):
        profile = choose_speech_profile("Olá.", "Posso ajudar com isso.")
        result = prepare_spoken_reply("Posso ajudar com isso.", "Olá.", profile)
        self.assertEqual(result, "Posso ajudar com isso.")
        self.assertNotIn("hmm", result.casefold())

    def test_empty_input_stays_empty(self):
        self.assertEqual(clean_speech_text("  "), "")
        self.assertEqual(prepare_spoken_reply("", "Olá"), "")


if __name__ == "__main__":
    unittest.main()
