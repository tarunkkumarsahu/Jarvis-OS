from types import SimpleNamespace

import providers.ollama_provider as ollama_provider_module
from providers.ollama_provider import OllamaProvider


def make_response(content="", tool_calls=None):
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
    )
    return SimpleNamespace(message=message)


def make_tool_call(name, arguments=None):
    function = SimpleNamespace(
        name=name,
        arguments=arguments or {},
    )
    return SimpleNamespace(function=function)


def test_provider_executes_tool_and_returns_final_response():
    calls = []
    events = []

    responses = iter(
        [
            make_response(tool_calls=[make_tool_call("current_time")]),
            make_response(content="It is 10:30 PM."),
        ]
    )

    def fake_chat(**kwargs):
        calls.append(kwargs)
        return next(responses)

    def executor(tool_name, arguments):
        assert tool_name == "current_time"
        assert arguments == {}
        return "22:30"

    provider = OllamaProvider(chat_fn=fake_chat)
    result = provider.generate(
        "what time is it?",
        tools=[{"type": "function", "function": {"name": "current_time"}}],
        executor=executor,
        event_handler=lambda name, payload: events.append((name, payload)),
    )

    assert result == "It is 10:30 PM."
    assert len(calls) == 2
    assert [name for name, _ in events] == ["tool_started", "tool_finished"]

    second_messages = calls[1]["messages"]
    assert second_messages[-1]["role"] == "tool"
    assert second_messages[-1]["content"] == "22:30"


def test_provider_can_use_multiple_tool_rounds():
    responses = iter(
        [
            make_response(tool_calls=[make_tool_call("first")]),
            make_response(tool_calls=[make_tool_call("second")]),
            make_response(content="done"),
        ]
    )
    executed = []

    provider = OllamaProvider(chat_fn=lambda **kwargs: next(responses))
    result = provider.generate(
        "do a multi-step task",
        tools=[{"type": "function", "function": {"name": "first"}}],
        executor=lambda name, arguments: executed.append(name) or f"{name}-result",
    )

    assert result == "done"
    assert executed == ["first", "second"]


def test_provider_keeps_bounded_conversation_history():
    captured_messages = []

    def fake_chat(**kwargs):
        captured_messages.append(kwargs["messages"])
        return make_response(content="answer")

    provider = OllamaProvider(chat_fn=fake_chat, history_turns=1)
    provider.generate("first question")
    provider.generate("second question")

    second_call = captured_messages[1]
    assert {"role": "user", "content": "first question"} in second_call
    assert {"role": "assistant", "content": "answer"} in second_call

    provider.clear_history()
    assert provider.history == []


def test_provider_degrades_gracefully_when_ollama_package_is_missing(monkeypatch):
    monkeypatch.setattr(ollama_provider_module, "_ollama", None)

    provider = ollama_provider_module.OllamaProvider()

    assert provider.status == "UNAVAILABLE"
    assert provider.available is False

    result = provider.generate("how are you?")

    assert "Local AI is unavailable right now" in result
    assert "python -m pip install -r requirements.txt" in result


def test_injected_chat_function_still_works_without_ollama_package(monkeypatch):
    monkeypatch.setattr(ollama_provider_module, "_ollama", None)

    provider = ollama_provider_module.OllamaProvider(
        chat_fn=lambda **kwargs: make_response(content="ready")
    )

    assert provider.status == "READY"
    assert provider.available is True
    assert provider.generate("hello") == "ready"
