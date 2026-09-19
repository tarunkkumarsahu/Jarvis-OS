import ast
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from interface import windows_startup as startup


class FakeKey:
    def __init__(self, registry):
        self.registry = registry

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeRegistry:
    HKEY_CURRENT_USER = 1
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}

    def OpenKey(self, root, path, reserved=0, access=0):
        if root != self.HKEY_CURRENT_USER or path != startup.RUN_KEY:
            raise FileNotFoundError(path)
        return FakeKey(self)

    def CreateKeyEx(self, root, path, reserved, access):
        self.OpenKey(root, path, reserved, access)
        return FakeKey(self)

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], self.REG_SZ

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = value

    def DeleteValue(self, key, name):
        del self.values[name]


class WindowsStartupTests(unittest.TestCase):
    def test_default_cli_does_not_enable_startup(self):
        from main import parse_args
        with patch("sys.argv", ["main.py"]):
            args = parse_args()
        self.assertFalse(args.enable_autostart)
        self.assertFalse(args.disable_autostart)
        self.assertFalse(args.autostart_status)

    def test_enable_only_writes_current_user_run_entry_after_request(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = FakeRegistry()
            command = subprocess.list2cmdline(
                ["C:/Python/pythonw.exe", str(Path(folder) / "startup_launcher.py")]
            )
            self.assertEqual(registry.values, {})
            with patch.object(startup, "startup_command", return_value=command):
                self.assertIn("will start", startup.enable_autostart(folder, registry=registry))
                self.assertEqual(registry.values[startup.VALUE_NAME], command)
                self.assertIn("enabled", startup.startup_status(folder, registry=registry))

    def test_does_not_overwrite_unrelated_startup_entry(self):
        registry = FakeRegistry()
        registry.values[startup.VALUE_NAME] = "other-application.exe"
        with patch.object(startup, "startup_command", return_value="our-pythonw.exe our-launcher.py"):
            with self.assertRaises(RuntimeError):
                startup.enable_autostart(".", registry=registry)
        self.assertEqual(registry.values[startup.VALUE_NAME], "other-application.exe")

    def test_disable_works_after_python_venv_is_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = FakeRegistry()
            launcher = str(Path(folder).resolve() / "startup_launcher.py")
            registry.values[startup.VALUE_NAME] = subprocess.list2cmdline(
                ["C:/old-venv/pythonw.exe", launcher]
            )
            self.assertIn("disabled", startup.disable_autostart(folder, registry=registry))
            self.assertNotIn(startup.VALUE_NAME, registry.values)

    def test_disable_does_not_remove_different_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = FakeRegistry()
            registry.values[startup.VALUE_NAME] = "C:/another-jarvis/startup_launcher.py"
            with self.assertRaises(RuntimeError):
                startup.disable_autostart(folder, registry=registry)
            self.assertIn(startup.VALUE_NAME, registry.values)

    def test_source_files_parse_and_presence_has_explicit_quit(self):
        root = Path(__file__).resolve().parents[1]
        for relative in (
            "interface/windows_startup.py", "interface/desktop_presence.py",
            "interface/operating_app.py", "startup_launcher.py", "main.py",
        ):
            with self.subTest(relative=relative):
                ast.parse((root / relative).read_text(encoding="utf-8"))
        app = (root / "interface/operating_app.py").read_text(encoding="utf-8")
        self.assertIn("self.desktop_presence.show_orb()", app)
        self.assertIn("self._quit_requested = True", app)
        self.assertIn("self.desktop_presence.shutdown()", app)


if __name__ == "__main__":
    unittest.main()
