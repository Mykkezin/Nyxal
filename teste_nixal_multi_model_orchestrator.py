from __future__ import annotations

import unittest
from unittest.mock import Mock

from nixal_multi_model_orchestrator import NyxalMultiModelOrchestrator


class TestNyxalMultiModelOrchestrator(unittest.TestCase):
    def setUp(self):
        self.hub = NyxalMultiModelOrchestrator(timeout_seconds=2, max_parallel=2)

    def test_default_local_only_never_calls_remote(self):
        openai = Mock(return_value="GPT")
        gemini = Mock(return_value="Gemini")
        result = self.hub.run("hello", providers={"openai": openai, "gemini": gemini})
        self.assertEqual(result.status, "local_only_no_remote_call")
        openai.assert_not_called()
        gemini.assert_not_called()

    def test_parallel_calls_both_and_synthesizes_locally(self):
        openai = Mock(return_value="A")
        gemini = Mock(return_value="B")
        synth = Mock(return_value="Nyxal synthesis")
        result = self.hub.run(
            "compare", mode="parallel_review",
            providers={"openai": openai, "gemini": gemini}, synthesize=synth,
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual({x.provider for x in result.results}, {"openai", "gemini"})
        self.assertEqual(result.synthesis, "Nyxal synthesis")
        self.assertEqual(result.synthesis_provider, "nyxal_local")
        synth.assert_called_once()

    def test_partial_failure_is_reported_and_success_is_preserved(self):
        def fail(_):
            raise RuntimeError("do not expose message")
        result = self.hub.run(
            "task", mode="parallel_review",
            providers={"openai": fail, "gemini": lambda _: "valid"},
        )
        self.assertEqual(result.status, "partial_success")
        failed = next(x for x in result.results if x.provider == "openai")
        self.assertEqual(failed.error, "RuntimeError")
        self.assertNotIn("do not expose", str(result.as_dict()))

    def test_no_configured_providers_is_explicit(self):
        result = self.hub.run("task", mode="parallel_review")
        self.assertEqual(result.status, "no_provider_configured")

    def test_select_one_requires_explicit_provider(self):
        with self.assertRaises(ValueError):
            self.hub.run("task", mode="select_one")
        result = self.hub.run(
            "task", mode="select_one", selected_provider="gemini",
            providers={"gemini": lambda _: "ok"},
        )
        self.assertEqual(result.status, "completed")

    def test_sequential_critique_passes_first_answer_as_untrusted_material(self):
        seen = []
        def first(_):
            return "draft answer"
        def critic(prompt):
            seen.append(prompt)
            return "critique"
        result = self.hub.run(
            "task", mode="sequential_critique",
            providers={"openai": first, "gemini": critic},
        )
        self.assertEqual(result.status, "completed")
        self.assertIn("material não confiável", seen[0])
        self.assertIn("draft answer", seen[0])

    def test_rejects_unknown_provider_and_invalid_mode(self):
        with self.assertRaises(ValueError):
            self.hub.run("task", mode="parallel_review", providers={"hermes": lambda _: "x"})
        with self.assertRaises(ValueError):
            self.hub.run("task", mode="unrestricted")

    def test_rejects_empty_task_and_invalid_limits(self):
        with self.assertRaises(ValueError):
            self.hub.run(" ")
        with self.assertRaises(ValueError):
            NyxalMultiModelOrchestrator(timeout_seconds=0)
        with self.assertRaises(ValueError):
            NyxalMultiModelOrchestrator(max_parallel=3)

    def test_adapter_errors_do_not_leak_exception_messages(self):
        def fail(_):
            raise RuntimeError("secret or prompt content")
        result = self.hub.run("task", mode="select_one", selected_provider="openai", providers={"openai": fail})
        self.assertEqual(result.results[0].error, "RuntimeError")
        self.assertNotIn("secret or prompt content", str(result.as_dict()))


if __name__ == "__main__":
    unittest.main()
