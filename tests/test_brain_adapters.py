"""Phase 3.5 tests — native BYOA adapters, tool translation, and router selection.

Provider streams are canned SSE lines injected via a fake transport, so no network is hit.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.brain.providers.anthropic import AnthropicAdapter  # noqa: E402
from services.brain.providers.base import Message, ProviderConfig  # noqa: E402
from services.brain.providers.gemini import GeminiAdapter  # noqa: E402
from services.brain.providers.openai import OpenAIAdapter, OpenAICompatAdapter  # noqa: E402
from services.brain.router import select_brain  # noqa: E402
from services.brain.tools.bridge import skills_to_tools  # noqa: E402
from services.brain.tools.translate import translate_tools  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402


def canned(lines):
    async def _transport(url, headers, body):
        _transport.captured = (url, headers, body)
        for ln in lines:
            yield ln

    return _transport


def collect(agen):
    async def _c():
        return [d async for d in agen]

    return asyncio.run(_c())


# --- streaming parse ---------------------------------------------------------------

def test_anthropic_stream_text_and_tool():
    lines = [
        'data: {"type":"content_block_start","content_block":{"type":"tool_use","name":"timer.SET_TIMER","id":"t1"}}',
        'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Olá"}}',
        'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":" mundo"}}',
    ]
    a = AnthropicAdapter(ProviderConfig(model="claude-x", api_key="k"), transport=canned(lines))
    deltas = collect(a.stream([Message(role="user", content="oi")]))
    assert "".join(d.text for d in deltas) == "Olá mundo"
    tools = [d.tool_call for d in deltas if d.tool_call]
    assert tools and tools[0]["name"] == "timer.SET_TIMER"


def test_openai_stream_text_and_tool_and_done():
    lines = [
        'data: {"choices":[{"delta":{"content":"Oi"}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"function":{"name":"timer.SET_TIMER","arguments":"{}"}}]}}]}',
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":"IGNORED"}}]}',  # after DONE, not emitted
    ]
    a = OpenAIAdapter(ProviderConfig(model="gpt-x", api_key="k"), transport=canned(lines))
    deltas = collect(a.stream([Message(role="user", content="oi")]))
    assert "".join(d.text for d in deltas) == "Oi"
    assert [d.tool_call["name"] for d in deltas if d.tool_call] == ["timer.SET_TIMER"]


def test_gemini_stream_text_and_tool():
    lines = [
        'data: {"candidates":[{"content":{"parts":[{"text":"Olá"}]}}]}',
        'data: {"candidates":[{"content":{"parts":[{"functionCall":{"name":"timer.SET_TIMER","args":{}}}]}}]}',
    ]
    a = GeminiAdapter(ProviderConfig(model="gemini-x", api_key="k"), transport=canned(lines))
    deltas = collect(a.stream([Message(role="user", content="oi")]))
    assert "".join(d.text for d in deltas) == "Olá"
    assert [d.tool_call["name"] for d in deltas if d.tool_call] == ["timer.SET_TIMER"]


# --- request building --------------------------------------------------------------

def test_anthropic_build_puts_system_and_tools():
    tools = skills_to_tools([TimerSkill()])
    a = AnthropicAdapter(ProviderConfig(model="claude-x", api_key="secret"))
    url, headers, body = a._build([Message("system", "seja breve"), Message("user", "oi")], tools)
    assert url.endswith("/v1/messages")
    assert headers["x-api-key"] == "secret"
    assert body["system"] == "seja breve"
    assert body["tools"][0]["name"].startswith("timer.")  # anthropic-native passthrough


def test_openai_compat_requires_base_url():
    try:
        OpenAICompatAdapter(ProviderConfig(model="x", api_key="k"))
        assert False, "expected ValueError without base_url"
    except ValueError:
        pass
    a = OpenAICompatAdapter(ProviderConfig(model="x", api_key="k", base_url="https://openrouter.ai/api"))
    url, _, body = a._build([Message("user", "oi")], None)
    assert url == "https://openrouter.ai/api/v1/chat/completions"
    assert body["stream"] is True


# --- tool translation --------------------------------------------------------------

def test_translate_tools_per_provider():
    tools = skills_to_tools([TimerSkill()])
    assert translate_tools(tools, "anthropic") == tools  # passthrough
    openai = translate_tools(tools, "openai")
    assert openai[0]["type"] == "function" and "parameters" in openai[0]["function"]
    gemini = translate_tools(tools, "gemini")
    assert "function_declarations" in gemini[0]
    assert gemini[0]["function_declarations"][0]["name"] == tools[0]["name"]


# --- router selection --------------------------------------------------------------

def test_router_selects_native_adapters():
    assert select_brain({"brain": {"kind": "anthropic", "model": "c"}}).name == "anthropic"
    assert select_brain({"brain": {"kind": "openai", "model": "g"}}).name == "openai"
    assert select_brain({"brain": {"kind": "gemini", "model": "x"}}).name == "gemini"
    assert select_brain({}).name == "local"
    assert select_brain({"brain": {"kind": "bogus", "model": "x"}}).name == "local"


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
            print(f"ok  {fn.__name__}")
    print("all brain-adapter tests passed")
