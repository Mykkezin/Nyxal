"""Deterministic signal and command tests; no microphone access is needed."""

import struct
import unittest

from nyxal_clap_wake import TwoClapDetector, is_rest_command


def clap_frame(amplitude=28000, samples=160):
    values = [0] * samples
    values[8] = amplitude
    return struct.pack(f"<{samples}h", *values)


class ClapWakeTests(unittest.TestCase):
    def test_two_claps_wake_within_window(self):
        detector = TwoClapDetector()
        self.assertFalse(detector.feed(clap_frame(), now=1.0))
        self.assertTrue(detector.feed(clap_frame(), now=1.45))

    def test_single_clap_does_not_wake(self):
        detector = TwoClapDetector()
        self.assertFalse(detector.feed(clap_frame(), now=1.0))
        self.assertFalse(detector.feed(bytes(320), now=1.4))

    def test_claps_outside_window_do_not_wake(self):
        detector = TwoClapDetector()
        self.assertFalse(detector.feed(clap_frame(), now=1.0))
        self.assertFalse(detector.feed(clap_frame(), now=2.1))

    def test_rest_commands_are_pt_br_case_and_accent_insensitive(self):
        self.assertTrue(is_rest_command("Nyxal, pode descansar."))
        self.assertTrue(is_rest_command("Nixau, pode descansar."))
        self.assertTrue(is_rest_command("Nixal, entre em repouso."))
        self.assertTrue(is_rest_command("entre em repouso"))
        self.assertFalse(is_rest_command("Nyxal, você pode me ajudar?"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
