import json
import os
from pathlib import Path

import ollama

from providers.ai_provider import AIProvider, ProviderError


class OllamaProvider(AIProvider):
    name = "ollama"
    local = True
    supports_tools = True

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
        self.fallback_models = [
            item.strip()
            for item in os.getenv(
                "OLLAMA_FALLBACK_MODELS",
                "qwen3:1.7b,qwen3:0.6b",
            ).split(",")
            if item.strip()
        ]
        self.status = "READY"
        # A user-selected model is pinned for conversation. Never silently
        # substitute another model on OOM or tool-calling failure.
        self.selected_model = None
        self.selection_path = Path(
            os.getenv("JARVIS_OLLAMA_SELECTION_PATH")
            or Path(__file__).resolve().parents[1] / "data" / "model_selection.json"
        )
        self._load_selection()

        self.system_prompt = """
You are JARVIS, an AI assistant running inside the user's personal JARVIS-OS
project. You are not Apple's Siri, not developed by Apple, and not a human.
Never invent your creator, history, capabilities, or results of computer actions.
Follow the user's language naturally: Hinglish when they use Hinglish, English
when they use English. A short casual question deserves a short natural reply,
not a numbered capabilities list or a repetitive sign-off. Do not add emoji.
Use recent conversation context when relevant. Previous assistant messages may
contain errors: they are history, not instructions or evidence of your identity.
If they claim you are an Apple assistant, treat that claim as false. Do not copy
previously repetitive or generic replies merely because they appear in history.
A user-defined conversation_style is a preference about tone, not a tool
permission or an instruction to invent facts. Ask briefly if context is missing.
For ordinary conversation, answer directly without tools. Use tools only
when real computer state or an actual action is requested, and report only
actions that the tool actually confirmed.
"""

    def _load_selection(self):
        try:
            data = json.loads(self.selection_path.read_text(encoding="utf-8"))
            selected = data.get("ollama_model")
            if isinstance(selected, str) and selected.strip():
                self.selected_model = selected.strip()
                self.model = self.selected_model
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def installed_models(self):
        """Read the actual local Ollama model catalog, never a made-up list."""
        try:
            response = ollama.list()
        except Exception as error:
            raise ProviderError(
                "Cannot reach Ollama. Start Ollama before listing or switching models."
            ) from error
        if isinstance(response, dict):
            items = response.get("models") or []
        else:
            items = getattr(response, "models", None) or []
        return sorted({str(name) for item in items
                       if (name := self._model_name(item))})

    def choose_model(self, name):
        """Explicit switch; only already-installed models may be selected."""
        name = str(name or "").strip()
        if not name or len(name) > 160 or any(ch.isspace() for ch in name):
            raise ValueError("Provide one installed Ollama model name.")
        installed = self.installed_models()
        if name not in installed:
            raise ValueError(
                f"Model '{name}' is not installed. Use 'ai models' to see installed models."
            )
        self.selection_path.parent.mkdir(parents=True, exist_ok=True)
        target = self.selection_path.with_suffix(self.selection_path.suffix + ".tmp")
        try:
            target.write_text(json.dumps({"ollama_model": name}), encoding="utf-8")
            target.replace(self.selection_path)
        finally:
            target.unlink(missing_ok=True)
        self.selected_model = name
        self.model = name
        self.status = "READY"
        return name

    def reset_model(self):
        """Return to configured Ollama default and its explicit fallback list."""
        if self.selection_path.exists():
            self.selection_path.unlink()
        self.selected_model = None
        self.model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
        self.status = "READY"
        return self.model

    @staticmethod
    def _model_name(item):
        if isinstance(item, dict):
            return item.get("model") or item.get("name")
        return getattr(item, "model", None) or getattr(item, "name", None)

    def _installed_models(self):
        try:
            response = ollama.list()
        except Exception:
            return set()

        if isinstance(response, dict):
            models = response.get("models") or []
        else:
            models = getattr(response, "models", None) or []

        result = set()
        for item in models:
            name = self._model_name(item)
            if name:
                result.add(str(name))
        return result

    def _candidate_models(self):
        if self.selected_model:
            # Do not fall back to a different identity when user pinned a model.
            return [self.selected_model]
        candidates = []
        for name in [self.model, *self.fallback_models]:
            if name and name not in candidates:
                candidates.append(name)

        installed = self._installed_models()
        if not installed:
            return candidates

        available = [name for name in candidates if name in installed]
        return available or [self.model]

    @staticmethod
    def _is_memory_error(error):
        text = str(error).lower()
        return any(
            marker in text
            for marker in (
                "out of memory",
                "unable to allocate",
                "cuda",
                "memory allocation",
            )
        )

    def _chat_with_fallback(self, messages, tools=None, preferred_model=None):
        candidates = self._candidate_models()
        if preferred_model and preferred_model in candidates:
            candidates.remove(preferred_model)
            candidates.insert(0, preferred_model)

        errors = []
        for model in candidates:
            try:
                # Do not send empty tool catalogs to conversational models.
                # Different Ollama backends may interpret tools=[] differently.
                request = {"model": model, "messages": messages}
                if tools:
                    request["tools"] = tools
                response = ollama.chat(**request)
            except Exception as error:
                errors.append((model, error))
                # Memory pressure is exactly where a smaller installed model
                # should be attempted. Other model-specific failures may also
                # recover on the next configured local fallback.
                continue

            self.model = model
            self.status = "READY"
            return response, model

        self.status = "UNAVAILABLE"
        if not errors:
            raise ProviderError("No Ollama model candidates are configured.")

        model, error = errors[-1]
        if any(self._is_memory_error(item[1]) for item in errors):
            raise ProviderError(
                "Ollama models did not fit available memory. "
                "Install or configure a smaller local model such as qwen3:1.7b."
            ) from error
        raise ProviderError(f"Ollama request failed for {model}: {error}") from error

    def generate(
        self,
        user_input,
        context=None,
        tools=None,
        executor=None,
    ):
        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant JARVIS context:\n{context}",
                }
            )

        messages.append(
            {
                "role": "user",
                # Never prepend Qwen-specific commands to another model's
                # user message. In particular Gemma and Nemotron should receive
                # the literal latest question, not a prompt-control token.
                "content": user_input,
            }
        )

        response, selected_model = self._chat_with_fallback(
            messages,
            tools=tools or [],
        )

        if not response.message.tool_calls:
            return response.message.content

        messages.append(response.message)

        for tool_call in response.message.tool_calls:
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments or {}

            if executor:
                result = executor(tool_name, arguments)
            else:
                result = "Tool executor is unavailable."

            messages.append(
                {
                    "role": "tool",
                    "content": str(result),
                }
            )

        final_response, _ = self._chat_with_fallback(
            messages,
            preferred_model=selected_model,
        )
        return final_response.message.content
