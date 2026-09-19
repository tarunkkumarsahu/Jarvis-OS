import unittest
from types import SimpleNamespace

from core.router import CommandRouter


class FakeOllama:
    is_available = True
    model = "gemma3:4b"

    def __init__(self):
        self.calls = []

    def generate(self, user_input, context=None, tools=None, executor=None):
        self.calls.append((user_input, context, tools))
        if "black holes" in user_input:
            return "Black holes have event horizons that even light cannot escape."
        return "A Python function is a reusable named block of code that runs when called."


class FakeRegistry:
    def __init__(self, provider):
        self.provider = provider
        self.names = []

    def get(self, name):
        self.names.append(name)
        if name != "ollama":
            raise AssertionError("Probe must never call an unrelated/cloud provider")
        return self.provider


class ChatProbeTests(unittest.TestCase):
    def test_local_probe_uses_two_distinct_questions_and_no_history_or_tools(self):
        provider = FakeOllama()
        registry = FakeRegistry(provider)
        router = CommandRouter.__new__(CommandRouter)
        router.brain = SimpleNamespace(
            orchestrator=SimpleNamespace(
                model_router=SimpleNamespace(registry=registry)
            )
        )
        output = router.route("chat probe")
        self.assertEqual(registry.names, ["ollama"])
        self.assertEqual(len(provider.calls), 2)
        self.assertNotEqual(provider.calls[0][0], provider.calls[1][0])
        self.assertTrue(all(context is None and tools is None for _, context, tools in provider.calls))
        self.assertIn("model=gemma3:4b", output)
        self.assertIn("Black holes", output)
        self.assertIn("Python function", output)
        self.assertIn("check answer relevance manually", output)

    def test_missing_local_backend_does_not_fall_back_to_paid_cloud(self):
        registry = FakeRegistry(FakeOllama())
        registry.provider.is_available = False
        router = CommandRouter.__new__(CommandRouter)
        router.brain = SimpleNamespace(
            orchestrator=SimpleNamespace(model_router=SimpleNamespace(registry=registry))
        )
        self.assertIn("unavailable", router.route("chat probe"))
        self.assertEqual(registry.provider.calls, [])


if __name__ == "__main__":
    unittest.main()
