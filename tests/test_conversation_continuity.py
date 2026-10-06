import tempfile
import unittest
from pathlib import Path

from core.context_builder import ContextBuilder
from core.orchestrator import Orchestrator
from memory.conversation_store import ConversationStore
from memory.memory_manager import MemoryManager
from tasks.task_manager import TaskManager
from tasks.task_store import TaskStore


class FakeConversationalModel:
    def __init__(self):
        self.contexts = []

    def generate(self, task, context=None, tools=None, executor=None):
        self.contexts.append(context or "")
        task.metadata["provider"] = "fake-test-provider"
        return "JARVIS answer to: " + task.raw_input


class NoTools:
    def get_tool_definitions(self):
        return []

    def execute(self, *args, **kwargs):
        raise AssertionError("Normal conversation should not execute tools")


class ConversationContinuityTests(unittest.TestCase):
    def test_turns_survive_reopening_and_return_oldest_first(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "jarvis.db"
            history = ConversationStore(db_path=path)
            history.add_turn("My name is Tarun", "Nice to meet you, Tarun.")
            history.add_turn("My project is JARVIS", "We can continue JARVIS.")

            after_restart = ConversationStore(db_path=path)
            turns = after_restart.recent_turns()
            self.assertEqual([x["user_text"] for x in turns],
                             ["My name is Tarun", "My project is JARVIS"])
            self.assertIn("Nice to meet you", after_restart.context())
            self.assertEqual(after_restart.clear(), 2)
            self.assertEqual(after_restart.recent_turns(), [])

    def test_conversation_context_reaches_next_model_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "jarvis.db"
            context_builder = ContextBuilder(
                memory_manager=MemoryManager(
                    memory_file=Path(folder) / "memory.json"
                ),
                conversation_store=ConversationStore(db_path=path),
            )
            model = FakeConversationalModel()
            tasks = TaskStore(db_path=path)
            orchestrator = Orchestrator(
                model_router=model,
                tool_registry=NoTools(),
                task_store=tasks,
                task_manager=TaskManager(store=tasks),
                context_builder=context_builder,
            )
            try:
                self.assertIn("My name is Tarun", orchestrator.handle("My name is Tarun"))
                self.assertIn("What is my name?", orchestrator.handle("What is my name?"))
                self.assertIn("My name is Tarun", model.contexts[1])
                self.assertNotIn("JARVIS answer to: My name is Tarun", model.contexts[1])
                self.assertIn("Recent USER utterances", model.contexts[1])
                self.assertEqual(len(ConversationStore(db_path=path).recent_turns()), 2)
            finally:
                orchestrator.shutdown()

    def test_context_injection_is_bounded_to_latest_turns(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ConversationStore(db_path=Path(folder) / "jarvis.db", max_turns=2)
            for number in range(5):
                store.add_turn(f"user {number}", f"jarvis {number}")
            context = store.context()
            self.assertNotIn("user 0", context)
            self.assertNotIn("user 2", context)
            self.assertIn("user 3", context)
            self.assertIn("user 4", context)

    def test_previous_repetitive_assistant_answers_do_not_poison_new_question(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ConversationStore(db_path=Path(folder) / "jarvis.db")
            stale = "Haan bol! Main kisi bhi task mein help kar sakta hoon. Let me know!"
            store.add_turn("What can you do?", stale)
            store.add_turn("Chrome pe search karke dekho", stale)
            store.add_turn("Mere system me kitne apps run ho rahe hain?", stale)
            recent = store.recent_user_context()
            self.assertIn("Chrome pe search", recent)
            self.assertIn("kitne apps run", recent)
            self.assertNotIn(stale, recent)
            self.assertEqual(len(store.recent_turns()), 3)  # UI history is preserved

    def test_user_context_is_bounded_and_preserves_latest_question(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ConversationStore(db_path=Path(folder) / "jarvis.db")
            for i in range(10):
                store.add_turn(f"question {i}", f"answer {i}")
            recent = store.recent_user_context(limit=3)
            self.assertNotIn("question 6", recent)
            self.assertIn("question 7", recent)
            self.assertIn("question 9", recent)
            self.assertNotIn("answer", recent)

    def test_conversation_can_be_disabled_without_deleting_history(self):
        from core.task import Task
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "jarvis.db"
            store = ConversationStore(db_path=path)
            store.add_turn("private conversation", "private reply")
            builder = ContextBuilder(
                memory_manager=MemoryManager(
                    memory_file=Path(folder) / "memory.json"
                ),
                conversation_store=store,
            )
            from unittest.mock import patch
            with patch.dict("os.environ", {"JARVIS_CONVERSATION_MEMORY_ENABLED": "false"}):
                self.assertIsNone(builder.build(Task(raw_input="Hello", intent="conversation")))
                self.assertFalse(builder.record_conversation_turn("x", "y"))
            self.assertEqual(len(store.recent_turns()), 1)


if __name__ == "__main__":
    unittest.main()
