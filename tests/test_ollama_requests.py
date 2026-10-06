import unittest
from types import SimpleNamespace
from unittest.mock import patch

from providers.ollama_provider import OllamaProvider


class OllamaRequestTests(unittest.TestCase):
    @patch("providers.ollama_provider.ollama.chat")
    @patch("providers.ollama_provider.ollama.list")
    def test_cross_model_request_preserves_exact_latest_question(self, installed, chat):
        installed.return_value = {"models": [{"model": "gemma3:4b"}]}
        chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="Black holes have event horizons.", tool_calls=[])
        )
        with patch.dict("os.environ", {
            "OLLAMA_MODEL": "gemma3:4b",
            "OLLAMA_FALLBACK_MODELS": "gemma3:4b",
        }):
            provider = OllamaProvider()
        question = "Explain black holes in one sentence."
        self.assertEqual(provider.generate(question, context="Earlier I was studying Python."),
                         "Black holes have event horizons.")
        payload = chat.call_args.kwargs
        self.assertEqual(payload["model"], "gemma3:4b")
        self.assertEqual(payload["messages"][-1], {"role": "user", "content": question})
        self.assertNotIn("/no_think", str(payload))
        self.assertNotIn("tools", payload)
        self.assertIn("Earlier I was studying Python.", payload["messages"][1]["content"])

    @patch("providers.ollama_provider.ollama.chat")
    @patch("providers.ollama_provider.ollama.list")
    def test_qwen_also_receives_literal_question_without_prompt_control_token(self, installed, chat):
        installed.return_value = {"models": [{"model": "qwen3:1.7b"}]}
        chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="A function groups reusable code.", tool_calls=[])
        )
        with patch.dict("os.environ", {
            "OLLAMA_MODEL": "qwen3:1.7b",
            "OLLAMA_FALLBACK_MODELS": "qwen3:1.7b",
        }):
            provider = OllamaProvider()
        question = "What is a Python function?"
        self.assertEqual(provider.generate(question), "A function groups reusable code.")
        self.assertEqual(chat.call_args.kwargs["messages"][-1]["content"], question)
        self.assertNotIn("tools", chat.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
