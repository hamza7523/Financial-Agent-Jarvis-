import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import generate_response


def test_generate_response_uses_gemini_helper(monkeypatch):
    def fake_call_gemini(prompt):
        assert "System prompt" in prompt
        assert "User asked" in prompt
        return "summary"

    monkeypatch.setattr("agent.call_gemini", fake_call_gemini)

    result = generate_response(
        user_query="test query",
        tool_name="demo_tool",
        tool_result={"ok": True},
        working_memory="System prompt",
    )

    assert result == "summary"
