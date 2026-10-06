# Multi-AI Brain V1 — local model selection

JARVIS can discover, select and persist any Ollama model **already installed** on
this computer. Gemma and Nemotron are not bundled, auto-downloaded or always
loaded into VRAM. This milestone adds explicit manual switching, not autonomous
multi-agent coordination, model quality certification or parallel inference.

## Install model files on your Windows PC

In PowerShell (with Ollama installed/running), for example:

```powershell
ollama pull gemma3:4b
ollama pull nemotron-3-nano:4b
ollama list
```

Check the model's actual official Ollama tag with `ollama list` before using it
in JARVIS. Download size is not the total VRAM/RAM requirement. Try one
model at a time if your laptop has limited memory.

Restart JARVIS using the tray menu's **Quit JARVIS** and then run:

```powershell
git switch feat/core-architecture-v1
git pull --ff-only origin feat/core-architecture-v1
.\.venv\Scripts\python.exe main.py
```

Inside the JARVIS chat box use these commands:

```text
ai models
ai model gemma3:4b
ai model
chat probe
Explain black holes in one sentence.
chat diagnostics
ai model nemotron-3-nano:4b
ai model auto
```

The exact installed model name is required. `ai model <name>` writes a local
selection file at `data/model_selection.json` (configurable via
`JARVIS_OLLAMA_SELECTION_PATH`). The preference survives restart and makes
Ollama the selected conversation provider, unless explicitly disabled through
`JARVIS_DISABLED_PROVIDERS`.

For explicit selections, JARVIS will **not silently substitute another Ollama
model** if the chosen model runs out of memory or has incompatible tools. Use
`ai model auto` to restore the `OLLAMA_MODEL` and
`OLLAMA_FALLBACK_MODELS` configuration and original provider-routing preference.

`ai models` does not install anything or execute a model. It lists models from
the running Ollama service. `chat probe` explicitly issues two synthetic
local model calls without chat history or computer tools. The request trace
shown in `chat diagnostics` contains counts, timings and provider/model names,
not your original prompts or response text.

## Scope and known limitations

- Selected models have not been validated for tool calling, Hinglish accuracy,
  or fit on the end user's Windows hardware. Test conversation first.
- Automatic per-task model assignment, model comparison, parallel execution,
  GPU budget enforcement, vision inputs and an interactive UI dropdown are
  future milestones. The current control is through existing chat commands.
- An explicit model selection is applied to the shared Ollama provider. A
  tool-using task may fail if that model cannot call tools; JARVIS must not
  claim the action succeeded.
- `clear conversation` removes saved conversational turns, not your selected
  model. `ai model auto` clears only the selected-model preference.
