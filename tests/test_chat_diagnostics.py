import unittest
from types import SimpleNamespace

from core.router import CommandRouter
from core.task import Task, TaskStatus


class FakeTaskStore:
    def __init__(self, tasks):
        self.tasks = tasks

    def list(self, limit=30):
        return self.tasks[:limit]


class ChatDiagnosticsTests(unittest.TestCase):
    def _router(self, tasks):
        router = CommandRouter.__new__(CommandRouter)
        model_router = SimpleNamespace(
            default_provider="auto",
            routing_mode="local_first",
            disabled_providers={"openai"},
        )
        orchestrator = SimpleNamespace(
            model_router=model_router,
            task_store=FakeTaskStore(tasks),
        )
        router.brain = SimpleNamespace(orchestrator=orchestrator)
        return router

    def _conversation_task(self, question, result, model="qwen3:1.7b"):
        task = Task(raw_input=question, intent="conversation")
        task.status = TaskStatus.COMPLETED
        task.metadata = {
            "provider": "ollama", "model": model,
            "routing_attempts": [
                {"provider": "ollama", "status": "success", "error": "secret-error"}
            ],
        }
        task.result = result
        return task

    def test_model_and_routes_visible_without_chat_content_or_secrets(self):
        first = self._conversation_task("private user question", "Private assistant reply " * 9)
        other = Task(raw_input="open notepad", intent="application")
        router = self._router([other, first])
        result = router.route("chat diagnostics")
        self.assertIn("model=qwen3:1.7b", result)
        self.assertIn("ollama:success", result)
        self.assertIn("Disabled providers: openai", result)
        self.assertNotIn("private user question", result)
        self.assertNotIn("Private assistant reply", result)
        self.assertNotIn("secret-error", result)

    def test_exact_repeated_model_reply_flagged(self):
        reply = "This is the same generic answer about capabilities. " * 4
        recent = self._conversation_task("What can you do?", reply)
        older = self._conversation_task("Explain black holes", reply)
        recent.metadata["conversation_retry"] = "stale_answer_detected"
        router = self._router([recent, older])
        result = router.route("conversation diagnostics")
        self.assertEqual(result.count("duplicate_reply=yes"), 1)
        self.assertIn("retry=stale_answer_detected", result)
        self.assertNotIn(reply, result)

    def test_no_conversation_tasks_reports_no_ai_calls(self):
        router = self._router([])
        result = router.route("chat diagnostics")
        self.assertIn("No conversation tasks yet", result)


if __name__ == "__main__":
    unittest.main()
