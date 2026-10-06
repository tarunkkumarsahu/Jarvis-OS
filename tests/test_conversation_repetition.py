import tempfile
import unittest
from pathlib import Path

from core.conversation_quality import is_stale_reply
from core.context_builder import ContextBuilder
from core.orchestrator import Orchestrator
from core.task import TaskStatus
from memory.conversation_store import ConversationStore
from memory.memory_manager import MemoryManager
from tasks.task_manager import TaskManager
from tasks.task_store import TaskStore


OLD_REPLY = ("Haan bhai! Main koi bhi task kar sakta hoon, coding ho ya apps. "
             "Let me know what you want to do and I will help you with it.")


class FakeConversationalModel:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def generate(self, task, context=None, tools=None, executor=None):
        self.calls.append((task.raw_input, context or "", tools))
        task.metadata["provider"] = "fake-local"
        return self.replies.pop(0)


class NoTools:
    def get_tool_definitions(self):
        return []

    def execute(self, *args, **kwargs):
        raise AssertionError("Conversation retry must not execute any desktop tools")


class RepetitionTests(unittest.TestCase):
    def test_different_questions_with_stale_long_response_detected(self):
        previous = [{"user_text": "What can you do?", "assistant_text": OLD_REPLY}]
        self.assertTrue(is_stale_reply("Explain black holes", OLD_REPLY, previous))
        self.assertFalse(is_stale_reply("What can you do?", OLD_REPLY, previous))
        self.assertFalse(is_stale_reply("Explain black holes", "Sure.", previous))
        self.assertFalse(is_stale_reply("Explain black holes", "A black hole bends spacetime.", previous))

    def _run_case(self, responses):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "jarvis.db"
        history = ConversationStore(db_path=path)
        history.add_turn("What can you do?", OLD_REPLY)
        context = ContextBuilder(
            memory_manager=MemoryManager(memory_file=Path(directory.name) / "memory.json"),
            conversation_store=history,
        )
        model = FakeConversationalModel(responses)
        tasks = TaskStore(db_path=path)
        orchestrator = Orchestrator(
            model_router=model,
            tool_registry=NoTools(),
            context_builder=context,
            task_store=tasks,
            task_manager=TaskManager(store=tasks),
        )
        return directory, history, model, tasks, orchestrator

    def test_repetition_retries_once_with_latest_user_message_and_no_old_history(self):
        directory, history, model, tasks, engine = self._run_case(
            [OLD_REPLY, "A black hole is a region where gravity prevents light from escaping."]
        )
        try:
            result = engine.handle("Explain black holes")
            self.assertIn("black hole", result.lower())
            self.assertEqual(len(model.calls), 2)
            self.assertEqual(model.calls[0][0], "Explain black holes")
            self.assertEqual(model.calls[1][0], "Explain black holes")
            self.assertNotIn("Recent USER utterances", model.calls[1][1])
            self.assertIsNone(model.calls[1][2])
            self.assertEqual(tasks.list(limit=1)[0].metadata["conversation_retry"], "recovered")
            self.assertEqual(len(history.recent_turns()), 2)
            self.assertEqual(history.recent_turns()[-1]["assistant_text"], result)
        finally:
            engine.shutdown()
            directory.cleanup()

    def test_repeated_retry_fails_instead_of_saving_misleading_reply(self):
        directory, history, model, tasks, engine = self._run_case([OLD_REPLY, OLD_REPLY])
        try:
            result = engine.handle("Explain black holes")
            self.assertIn("repeated an unrelated answer", result)
            self.assertEqual(len(model.calls), 2)
            self.assertEqual(len(history.recent_turns()), 1)
            self.assertEqual(tasks.list(limit=1)[0].status, TaskStatus.FAILED)
        finally:
            engine.shutdown()
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
