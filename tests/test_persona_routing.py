import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.router import CommandRouter
from memory.memory_manager import MemoryManager
from voice.voice_manager import VoiceManager


class FakeBrain:
    def __init__(self):
        self.calls = []

    def respond(self, value):
        self.calls.append(value)
        return "model response"


class PersonaRoutingTests(unittest.TestCase):
    def _router(self):
        router = CommandRouter.__new__(CommandRouter)
        router.brain = FakeBrain()
        router.memory = MemoryManager(
            memory_file=Path(self.folder.name) / "memory.json"
        )
        return router

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.folder.cleanup()

    def test_jarvis_invocation_is_short_and_model_free(self):
        router = self._router()
        self.assertEqual(router.route("Jarvis"), "Haan bhai, bol.")
        self.assertEqual(router.route("Hey Jarvis"), "Haan bhai, bol.")
        self.assertEqual(router.brain.calls, [])

    def test_identity_is_not_hallucinated_by_small_model(self):
        router = self._router()
        for utterance in ("Jarvis, tujhe kisne banaya?", "Who created you?"):
            answer = router.route(utterance)
            self.assertIn("JARVIS-OS", answer)
            self.assertIn("Tarun", answer)
            self.assertEqual(router.brain.calls, [])

    def test_style_choice_persists_on_disk(self):
        router = self._router()
        self.assertIn("Hinglish", router.route("speak casually"))
        self.assertIn("Hinglish", router.memory.snapshot()["conversation_style"])
        persisted = MemoryManager(
            memory_file=Path(self.folder.name) / "memory.json"
        ).snapshot()
        self.assertEqual(persisted["conversation_style"],
                         router.memory.snapshot()["conversation_style"])

    def test_speech_text_removes_emoji_but_keeps_words(self):
        voice = VoiceManager()
        self.assertEqual(voice.speech_text("Haan bhai 😊 baat karte hain 😁"),
                         "Haan bhai baat karte hain")


if __name__ == "__main__":
    unittest.main()
