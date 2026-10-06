# JARVIS desktop presence — Windows first build

This slice makes the *existing* JARVIS runtime available from a small desktop
presence; it does not install a new operating system or run a second assistant.

## Try the desktop presence

From PowerShell in the JARVIS repository:

```powershell
git switch feat/core-architecture-v1
git pull --ff-only origin feat/core-architecture-v1
.\.venv\Scripts\python.exe main.py
```

On a Windows desktop with a working system tray, JARVIS now has a tray icon.
Close the main window using its close control: the process should **remain
running** and a small draggable orb should appear near the desktop edge.
Click the orb, or click the tray icon, to restore the **same** Home/conversation
session. The tray menu also exposes **Quick command**, **Speak to JARVIS**, and
**Quit JARVIS**. Quick command uses the existing brain; it does not create
another process. Choose **Quit JARVIS** to stop the runtime completely.

If the OS has no system tray, the existing normal-window behavior is retained;
the application should not become an invisible, uncloseable background process.

## Optional startup after Windows sign-in

This is **off by default**. It only changes your account's Windows Run entry
when you explicitly enable it. It does not require admin permissions.

```powershell
.\.venv\Scripts\python.exe main.py --autostart-status
.\.venv\Scripts\python.exe main.py --enable-autostart
.\.venv\Scripts\python.exe main.py --disable-autostart
```

The installed sign-in entry runs this repository's `startup_launcher.py` with
the virtual environment's `pythonw.exe`. The launcher restores the repository
working directory and asks JARVIS to start with the **minimal orb** instead of
opening a fullscreen dashboard. If the Windows tray is unavailable at startup,
JARVIS falls back to the main window so the process remains visible.

Moving the repository or deleting/rebuilding the virtual environment can make
an existing sign-in entry stale. Disable startup **before moving the project**,
then re-enable from the new directory. Startup is not an installer and does not
keep Python or Ollama running automatically.

## What this milestone does not do

- It does not implement wake-word detection or a system-wide keyboard shortcut.
- The microphone button still uses the existing speech-recognition service.
- Local AI conversation still requires a running/configured Ollama or LM Studio
  provider. A tray icon does not make an unavailable model respond.
- GitHub Actions can test the startup ownership/CLI and syntax, but the Windows
  notification area, floating orb, microphone and sign-in launch require a real
  Windows desktop smoke test.
