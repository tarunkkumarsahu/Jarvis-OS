from __future__ import annotations

import json
from typing import Any, Callable

try:
    import ollama as _ollama
except ModuleNotFoundError:  # optional runtime dependency; deterministic JARVIS should still boot
    _ollama = None


EventHandler = Callable[[str, dict[str, Any]], None]
ToolExecutor = Callable[[str, dict[str, Any]], Any]


class OllamaProvider:
    """Local Ollama-backed language model provider with bounded tool execution.

    The provider owns model conversation history and the model/tool loop, but it
    does not own permissions, UI state, or tool implementations. Those remain in
    higher layers so the provider stays reusable.

    Ollama is treated as an optional runtime capability. If the Python package is
    missing, JARVIS can still boot and deterministic/local tools can still work;
    only requests that actually require the language model degrade gracefully.
    """

    def __init__(
        self,
        model: str = "qwen3:8b",
        chat_fn: Callable[..., Any] | None = None,
        max_tool_rounds: int = 4,
        history_turns: int = 6,
    ) -> None:
        self.model = model
        self.max_tool_rounds = max(1, max_tool_rounds)
        self.history_turns = max(0, history_turns)
        self.history: list[dict[str, str]] = []
        self.unavailable_reason: str | None = None

        if chat_fn is not None:
            self._chat = chat_fn
            self.status = "READY"
        elif _ollama is None:
            self._chat = None
            self.status = "UNAVAILABLE"
            self.unavailable_reason = (
                "The Python 'ollama' package is not installed in the active JARVIS "
                "environment. Deterministic commands are still available. Install "
                "project dependencies with: python -m pip install -r requirements.txt"
            )
        else:
            self._chat = _ollama.chat
            self.status = "READY"

        self.system_prompt = """You are JARVIS, a local personal AI assistant.

You have access to tools that represent capabilities already implemented on this computer.

Important rules:
- When the user's request requires a real system action, browser action, local inspection, or other external effect, use the matching tool.
- If a matching tool exists, you MUST use it instead of saying that you do not have that capability.
- Never claim that you performed an action unless a tool actually executed it.
- Use tool results as the source of truth for system facts and completed actions.
- If a tool result is an error or permission is denied, explain that result instead of pretending the action worked.
- Before telling the user that a requested computer action is unavailable, check the provided tool list for a matching capability.
- For normal conversation that requires no tool, answer directly.
- Match the user's language naturally. If the user speaks or writes Hindi or Hinglish, reply in natural Hindi/Hinglish instead of forcing English.
- Keep product names, app names, commands, paths, and technical identifiers in the form that is clearest to the user.
- Keep responses concise unless the user asks for detail.
"""

    @property
    def available(self) -> bool:
        return self._chat is not None

    def generate(
        self,
        user_input: str,
        tools: list[dict[str, Any]] | None = None,
        executor: ToolExecutor | None = None,
        event_handler: EventHandler | None = None,
    ) -> str:
        text = user_input.strip()
        if not text:
            return ""

        if self._chat is None:
            reason = self.unavailable_reason or "The local Ollama model provider is unavailable."
            return f"Local AI is unavailable right now. {reason}"

        tool_definitions = tools or []
        messages: list[Any] = [
            {"role": "system", "content": self.system_prompt},
            *self._history_context(),
            {"role": "user", "content": "/no_think\n" + text},
        ]

        tool_rounds = 0

        while True:
            response = self._chat(
                model=self.model,
                messages=messages,
                tools=tool_definitions,
            )

            message = self._value(response, "message")
            if message is None:
                raise RuntimeError("Ollama returned a response without a message.")

            tool_calls = self._value(message, "tool_calls", []) or []
            content = self._value(message, "content", "") or ""

            if not tool_calls:
                final_text = str(content).strip()
                if not final_text:
                    final_text = "I completed the request but received no final text."
                self._remember_turn(text, final_text)
                return final_text

            if tool_rounds >= self.max_tool_rounds:
                self._emit(
                    event_handler,
                    "agent_limit_reached",
                    max_tool_rounds=self.max_tool_rounds,
                )
                raise RuntimeError(
                    f"Model exceeded the tool round limit ({self.max_tool_rounds})."
                )

            tool_rounds += 1
            messages.append(message)

            for tool_call in tool_calls:
                function = self._value(tool_call, "function")
                tool_name = str(self._value(function, "name", "")).strip()
                arguments = self._normalise_arguments(
                    self._value(function, "arguments", {})
                )

                if not tool_name:
                    raise RuntimeError("The model requested a tool without a name.")

                self._emit(
                    event_handler,
                    "tool_started",
                    tool_name=tool_name,
                    arguments=arguments,
                    round=tool_rounds,
                )

                if executor is None:
                    result: Any = "Tool executor is unavailable."
                else:
                    result = executor(tool_name, arguments)

                self._emit(
                    event_handler,
                    "tool_finished",
                    tool_name=tool_name,
                    result=result,
                    round=tool_rounds,
                )

                messages.append(
                    {
                        "role": "tool",
                        "content": self._serialise_tool_result(result),
                        "tool_name": tool_name,
                    }
                )

    def clear_history(self) -> None:
        self.history.clear()

    def _history_context(self) -> list[dict[str, str]]:
        if self.history_turns == 0:
            return []
        max_messages = self.history_turns * 2
        return list(self.history[-max_messages:])

    def _remember_turn(self, user_text: str, assistant_text: str) -> None:
        if self.history_turns == 0:
            return

        self.history.extend(
            [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text},
            ]
        )

        max_messages = self.history_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    @staticmethod
    def _emit(
        event_handler: EventHandler | None,
        event_name: str,
        **payload: Any,
    ) -> None:
        if event_handler is not None:
            event_handler(event_name, payload)

    @staticmethod
    def _value(obj: Any, name: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    @staticmethod
    def _normalise_arguments(arguments: Any) -> dict[str, Any]:
        if arguments is None:
            return {}
        if isinstance(arguments, dict):
            return arguments
        if isinstance(arguments, str):
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        try:
            return dict(arguments)
        except (TypeError, ValueError):
            return {}

    @staticmethod
    def _serialise_tool_result(result: Any) -> str:
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(result)
