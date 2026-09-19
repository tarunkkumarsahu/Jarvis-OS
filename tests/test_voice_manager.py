import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch

from voice.voice_manager import VoiceManager


class VoiceManagerTests(unittest.TestCase):
    def test_clean_text_makes_screen_content_speakable(self):
        text = "## Result\nUse **JARVIS** and `main.py`. https://example.com"
        cleaned = VoiceManager.clean_text(text)

        self.assertEqual(cleaned, "Result Use JARVIS and main.py.")

    def test_long_response_is_clipped_for_voice_only(self):
        voice = VoiceManager()
        voice.max_speech_chars = 24

        result = voice.speech_text("This is a deliberately long response for the screen.")

        self.assertLess(len(result), 100)
        self.assertIn("rest of the response on screen", result)

    def test_optional_local_whisper_transcribes_and_reuses_model(self):
        made = []
        class FakeWhisperModel:
            def __init__(self, name, device, compute_type):
                made.append((name, device, compute_type))

            def transcribe(self, audio_file, **kwargs):
                self_last_path.append(audio_file)
                self_last_options.append(kwargs)
                return iter([SimpleNamespace(text=" Haan bhai "), SimpleNamespace(text=" kya haal hai ")]), None

        self_last_path = []
        self_last_options = []
        fake_package = SimpleNamespace(WhisperModel=FakeWhisperModel)
        voice = VoiceManager()
        voice.local_stt_model = "base"
        with patch.dict(sys.modules, {"faster_whisper": fake_package}):
            text1 = voice.transcribe_local_file("test1.wav")
            text2 = voice.transcribe_local_file("test2.wav")

        self.assertEqual(text1, "Haan bhai kya haal hai")
        self.assertEqual(text2, text1)
        self.assertEqual(made, [("base", "cpu", "int8")])
        self.assertEqual(self_last_path, ["test1.wav", "test2.wav"])
        self.assertTrue(all(option["vad_filter"] for option in self_last_options))
        self.assertTrue(all(option["language"] is None for option in self_last_options))

    @patch("voice.voice_manager.subprocess.run")
    def test_windows_tts_passes_text_through_environment(self, run):
        run.return_value.returncode = 0
        unsafe_text = "hello'; Remove-Item C:\\important; '"

        result = VoiceManager._speak_windows(unsafe_text)

        self.assertTrue(result)
        args, kwargs = run.call_args
        command = args[0]
        self.assertEqual(command[0], "powershell.exe")
        self.assertFalse(kwargs["shell"])
        self.assertNotIn(unsafe_text, " ".join(command))
        self.assertEqual(kwargs["env"]["JARVIS_TTS_TEXT"], unsafe_text)


if __name__ == "__main__":
    unittest.main()
