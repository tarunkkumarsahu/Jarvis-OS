"""Optional, per-user Windows sign-in startup for JARVIS.

Never changes Windows startup unless the user explicitly runs --enable-autostart.
Only the current user's Run key is used; no admin permissions or scheduled task.
"""
import os
import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "JarvisOS"


def startup_command(project_root, python_executable=None):
    """Build a Windows startup command with stable cwd and no visible console."""
    if os.name != "nt":
        raise RuntimeError("Automatic sign-in startup is supported only on Windows.")
    root = Path(project_root).expanduser().resolve()
    launcher = root / "startup_launcher.py"
    if not launcher.is_file():
        raise FileNotFoundError(f"JARVIS startup launcher is missing: {launcher}")
    executable = Path(python_executable or sys.executable).resolve()
    pythonw = executable.with_name("pythonw.exe")
    if not pythonw.is_file():
        raise FileNotFoundError(
            f"pythonw.exe was not found at {pythonw}. Use a Windows Python/venv installation."
        )
    return subprocess.list2cmdline([str(pythonw), str(launcher)])


def _read_value(registry):
    try:
        with registry.OpenKey(registry.HKEY_CURRENT_USER, RUN_KEY, 0, registry.KEY_READ) as key:
            value, _ = registry.QueryValueEx(key, VALUE_NAME)
            return str(value)
    except FileNotFoundError:
        return None


def startup_status(project_root, python_executable=None, registry=None):
    if os.name != "nt":
        return "Windows sign-in startup is not supported on this operating system."
    if registry is None:
        import winreg as registry
    current = _read_value(registry)
    if not current:
        return "JARVIS sign-in startup is disabled."
    try:
        expected = startup_command(project_root, python_executable)
    except (RuntimeError, FileNotFoundError) as error:
        return f"JARVIS sign-in startup entry exists, but its launcher is unavailable: {error}"
    if current != expected:
        return "A different JARVIS startup entry exists; it was not changed."
    return "JARVIS sign-in startup is enabled for your Windows account."


def enable_autostart(project_root, python_executable=None, registry=None):
    command = startup_command(project_root, python_executable)
    if registry is None:
        import winreg as registry
    current = _read_value(registry)
    if current and current != command:
        raise RuntimeError("A different JARVIS startup entry already exists. No changes made.")
    with registry.CreateKeyEx(
        registry.HKEY_CURRENT_USER, RUN_KEY, 0, registry.KEY_SET_VALUE
    ) as key:
        registry.SetValueEx(key, VALUE_NAME, 0, registry.REG_SZ, command)
    return "JARVIS will start after you sign in to Windows. You can disable it with --disable-autostart."


def disable_autostart(project_root, python_executable=None, registry=None):
    if os.name != "nt":
        raise RuntimeError("Automatic sign-in startup is supported only on Windows.")
    if registry is None:
        import winreg as registry
    current = _read_value(registry)
    if current is None:
        return "JARVIS sign-in startup is already disabled."
    # Never remove an entry we cannot identify as this project's launcher.
    expected = startup_command(project_root, python_executable)
    if current != expected:
        raise RuntimeError("The startup entry belongs to a different JARVIS installation; unchanged.")
    with registry.OpenKey(
        registry.HKEY_CURRENT_USER, RUN_KEY, 0, registry.KEY_SET_VALUE
    ) as key:
        registry.DeleteValue(key, VALUE_NAME)
    return "JARVIS sign-in startup is disabled."
