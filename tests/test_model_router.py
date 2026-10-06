import os
import unittest
from unittest.mock import patch

from core.task import Task
from models.model_router import ModelRouter


class FakeProvider:
    def __init__(self, name, local, supports_tools, result=None, available=True):
        self.name = name
        self.local = local
        self.supports_tools = supports_tools
        self.result = result or name
        self.is_available = available
        self.model = f"{name}-model"

    def generate(self, user_input, context=None, tools=None, executor=None):
        return self.result


class FakeRegistry:
    def __init__(self):
        self.providers = {
            "local": FakeProvider("local", True, True, result="local-result"),
            "cloud": FakeProvider("cloud", False, False, result="cloud-result"),
        }

    def names(self):
        return list(self.providers.keys())

    def get(self, name):
        return self.providers[name]


class ModelRouterTests(unittest.TestCase):
    def test_auto_routing_prefers_local_provider(self):
        router = ModelRouter(registry=FakeRegistry())
        router.default_provider = "auto"
        task = Task(raw_input="hello")

        result = router.generate(task)

        self.assertEqual(result, "local-result")
        self.assertEqual(task.metadata["provider"], "local")
        self.assertEqual(task.metadata["model"], "local-model")
        self.assertTrue(task.metadata["provider_local"])

    def test_request_trace_records_actual_new_input_without_leaking_conversation(self):
        registry = FakeRegistry()
        calls = []
        original_generate = registry.providers["local"].generate

        def capture(user_input, context=None, tools=None, executor=None):
            calls.append((user_input, context))
            return original_generate(user_input, context=context, tools=tools, executor=executor)

        registry.providers["local"].generate = capture
        router = ModelRouter(registry=registry)
        router.default_provider = "local"
        first = Task(raw_input="Explain black holes.")
        second = Task(raw_input="What is a Python function?")
        self.assertEqual(router.generate(first, context="old question"), "local-result")
        self.assertEqual(router.generate(second, context="new context"), "local-result")
        self.assertEqual(calls, [
            ("Explain black holes.", "old question"),
            ("What is a Python function?", "new context"),
        ])
        for task, message, context in (
            (first, "Explain black holes.", "old question"),
            (second, "What is a Python function?", "new context"),
        ):
            trace = task.metadata["model_trace"]
            self.assertEqual(trace["request_id"], task.task_id[:8])
            self.assertEqual(trace["input_chars"], len(message))
            self.assertEqual(trace["context_chars"], len(context))
            self.assertEqual(trace["response_chars"], len("local-result"))
            self.assertEqual(trace["provider_selected"], "local")
            self.assertEqual(trace["model_selected"], "local-model")
            self.assertEqual(trace["status"], "success")
            self.assertNotIn(message, str(trace))
            self.assertNotIn(context, str(trace))

    def test_explicit_cloud_provider_is_respected_without_tools(self):
        router = ModelRouter(registry=FakeRegistry())
        router.default_provider = "cloud"
        task = Task(raw_input="hello")

        result = router.generate(task)

        self.assertEqual(result, "cloud-result")
        self.assertEqual(task.metadata["provider"], "cloud")

    def test_tool_required_task_never_uses_provider_without_tools(self):
        registry = FakeRegistry()
        router = ModelRouter(registry=registry)
        router.default_provider = "cloud"
        task = Task(
            raw_input="create a reminder",
            requires_tools=True,
        )

        result = router.generate(
            task,
            tools=[{"type": "function", "function": {"name": "reminder"}}],
        )

        self.assertEqual(result, "local-result")
        self.assertEqual(task.metadata["provider"], "local")

    def test_tool_task_fails_closed_when_no_provider_can_execute_tools(self):
        registry = FakeRegistry()
        registry.providers["local"].supports_tools = False
        router = ModelRouter(registry=registry)
        task = Task(
            raw_input="do an action",
            requires_tools=True,
        )

        result = router.generate(
            task,
            tools=[{"type": "function", "function": {"name": "action"}}],
        )

        self.assertIn("tool calling support", result)
        self.assertNotIn("cloud-result", result)

    def test_legacy_ai_provider_does_not_force_cloud(self):
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "cloud"},
            clear=False,
        ):
            os.environ.pop("JARVIS_PROVIDER", None)
            router = ModelRouter(registry=FakeRegistry())

        self.assertEqual(router.default_provider, "auto")

    def test_disabled_provider_is_not_attempted(self):
        with patch.dict(
            os.environ,
            {"JARVIS_DISABLED_PROVIDERS": "cloud"},
            clear=False,
        ):
            router = ModelRouter(registry=FakeRegistry())

        task = Task(raw_input="hello")
        result = router.generate(task)

        self.assertEqual(result, "local-result")
        self.assertNotIn("cloud", [item["provider"] for item in task.metadata["routing_attempts"]])


if __name__ == "__main__":
    unittest.main()
