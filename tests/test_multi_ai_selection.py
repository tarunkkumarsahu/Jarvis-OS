import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.router import CommandRouter
from models.model_registry import ModelRegistry
from models.model_router import ModelRouter
from providers.ollama_provider import OllamaProvider


class LocalMultiAIModelTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "selected.json"
        self.env = patch.dict("os.environ", {
            "JARVIS_OLLAMA_SELECTION_PATH": str(self.path),
            "OLLAMA_MODEL": "qwen3:1.7b",
            "OLLAMA_FALLBACK_MODELS": "qwen3:1.7b,qwen3:0.6b",
            "JARVIS_PROVIDER": "auto",
            "JARVIS_DISABLED_PROVIDERS": "openai,lmstudio",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.folder.cleanup()

    def _catalog(self):
        return {"models": [
            {"model": "qwen3:1.7b"},
            {"model": "gemma3:4b"},
            {"model": "nemotron-3-nano:4b"},
        ]}

    @patch("providers.ollama_provider.ollama.list")
    @patch("providers.ollama_provider.ollama.chat")
    def test_switch_persists_and_pins_only_installed_model(self, chat, catalog):
        catalog.return_value = self._catalog()
        chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="I can explain black holes.", tool_calls=[])
        )
        provider = OllamaProvider()
        self.assertEqual(provider.installed_models(), [
            "gemma3:4b", "nemotron-3-nano:4b", "qwen3:1.7b",
        ])
        self.assertEqual(provider.choose_model("gemma3:4b"), "gemma3:4b")
        self.assertEqual(provider._candidate_models(), ["gemma3:4b"])
        self.assertEqual(provider.generate("Explain black holes."),
                         "I can explain black holes.")
        self.assertEqual(chat.call_args.kwargs["model"], "gemma3:4b")
        reopened = OllamaProvider()
        self.assertEqual(reopened.selected_model, "gemma3:4b")
        self.assertEqual(reopened._candidate_models(), ["gemma3:4b"])
        with self.assertRaises(ValueError):
            reopened.choose_model("imaginary-model:4b")
        self.assertEqual(reopened.selected_model, "gemma3:4b")
        self.assertEqual(reopened.reset_model(), "qwen3:1.7b")
        self.assertFalse(self.path.exists())
        self.assertIsNone(OllamaProvider().selected_model)

    @patch("providers.ollama_provider.ollama.list")
    def test_pinned_selection_is_preferred_after_restart(self, catalog):
        catalog.return_value = self._catalog()
        OllamaProvider().choose_model("nemotron-3-nano:4b")
        router = ModelRouter(registry=ModelRegistry())
        self.assertEqual(router.default_provider, "ollama")
        self.assertEqual(router.registry.get("ollama").selected_model,
                         "nemotron-3-nano:4b")

    @patch("providers.ollama_provider.ollama.list")
    def test_command_routing_switch_and_model_catalog(self, catalog):
        catalog.return_value = self._catalog()
        router = CommandRouter.__new__(CommandRouter)
        model_router = ModelRouter(registry=ModelRegistry())
        router.brain = SimpleNamespace(
            orchestrator=SimpleNamespace(model_router=model_router)
        )
        self.assertIn("gemma3:4b", router.route("ai models"))
        self.assertIn("Selected local Ollama model: gemma3:4b",
                      router.route("ai model gemma3:4b"))
        self.assertIn("(pinned)", router.route("ai model"))
        self.assertIn("not installed", router.route("ai model not-a-model:4b"))
        self.assertIn("selection reset", router.route("ai model auto"))

    @patch("providers.ollama_provider.ollama.list", side_effect=OSError("offline"))
    def test_no_fake_installed_catalog_when_ollama_offline(self, _catalog):
        provider = OllamaProvider()
        from providers.ai_provider import ProviderError
        with self.assertRaises(ProviderError):
            provider.installed_models()
        with self.assertRaises(ProviderError):
            provider.choose_model("gemma3:4b")


if __name__ == "__main__":
    unittest.main()
