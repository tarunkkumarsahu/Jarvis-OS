# JARVIS natural conversation — first working integration

This milestone **reuses open-source components** rather than writing speech or
language models from scratch. It adds bounded, persistent multi-turn context to
the existing JARVIS conversation path, plus an optional local speech recognizer.

## What was built

- `memory/conversation_store.py`: local SQLite turn pairs, latest 8 turns
  by default, loaded oldest-first into conversation context.
- `core/context_builder.py`: conversation-only recent-history retrieval;
  unrelated file and tool tasks do not receive this dialogue by default.
- `core/orchestrator.py`: append a turn only after a successful verified,
  model-backed conversational response. Failed providers and direct commands
  are not recorded as artificial AI replies.
- `interface/operating_app.py`: shows the last six saved turns on launch.
- Direct command `clear conversation` deletes saved dialogue only (not project
  sessions, task history, or explicit key-value memory).
- `JARVIS_CONVERSATION_MEMORY_ENABLED=false` disables new recording and
  automatic retrieval without erasing previously saved turns.
- `voice/voice_manager.py`: optional offline multilingual faster-whisper
  transcription, with a lazily loaded, cached CPU/int8 model. The existing
  Google recognition mode remains the default so installs are unchanged.

No microphone audio recordings are intentionally retained after transcription.
The text history is **stored locally** in `data/jarvis.db` (or `JARVIS_DB_PATH`).

## Windows smoke test

Open PowerShell in the existing JARVIS repo:

```powershell
git switch feat/core-architecture-v1
git pull --ff-only origin feat/core-architecture-v1
ollama list
ollama pull qwen3:1.7b
ollama run qwen3:1.7b
```

Once Ollama responds, leave its service running; exit the interactive prompt,
then run JARVIS from the repo in a separate PowerShell window:

```powershell
.\.venv\Scripts\python.exe main.py
```

Ask these **as actual AI questions**, not fixed command-router shortcuts:

1. `I am working on JARVIS and I want natural voice conversations.`
2. `What did I just say I am working on?`
3. Close JARVIS using **Quit JARVIS**, reopen it, and ask
   `What were we just discussing?`

JARVIS should show the last six saved model-backed turns after reopening.
The context of the second and third questions should include the prior
turns. Whether the answers are intelligent and accurate depends on the
configured model: a tiny local model may perform substantially worse than
a larger model, and this test must be verified on the user's computer.

To delete saved dialogue without deleting workspace context, type
`clear conversation`. To disable future dialogue recording, set
`JARVIS_CONVERSATION_MEMORY_ENABLED=false` in `.env`.

## Optional offline speech-to-text

Install the open-source faster-whisper package in the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pip install faster-whisper
```

Then set in `.env`:

```env
JARVIS_STT_BACKEND=whisper
JARVIS_STT_MODEL=base
```

The multilingual `base` model runs on CPU/int8 to avoid loading speech
recognition onto the same already-constrained GPU as the Ollama model. The
model may need to download on first use. English/Hindi code-switching accuracy
and latency must be tested rather than assumed. Switch back with
`JARVIS_STT_BACKEND=google` (online recognition).

**Limitation:** microphone recording is still the existing six-second,
push-to-talk capture. This is *not yet* a fully interruptible continuous
voice conversation or a wake-word listener.

## Verified open-source references and next integration

- [Pipecat](https://github.com/pipecat-ai/pipecat): a realtime voice-agent
  pipeline; evaluate as an **isolated audio runtime** rather than replacing
  the JARVIS task/router/permission architecture.
- [Windows local voice-agent example](https://github.com/vsukhwani/windows-voice-agent):
  useful practical reference for Whisper + Ollama + Kokoro TTS on Windows.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper): optional offline STT
  that we integrated for push-to-talk.
- [Silero VAD](https://github.com/snakers4/silero-vad): use next for
  speech-start/end detection instead of a fixed six-second recording.
- [openWakeWord](https://github.com/dscripka/openWakeWord): evaluate only
  after conversation, latency, interruption and mic privacy controls work.
  Its bundled pretrained wake-word models have noncommercial licensing
  restrictions; review model licensing before commercial distribution.

Next acceptance target: user talks without rigid commands -> speech end detected
-> JARVIS uses recent context -> model responds -> TTS plays -> user interrupts
and continues. This needs real Windows audio testing and a viable AI provider.
