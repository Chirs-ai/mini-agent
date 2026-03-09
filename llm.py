"""
统一 LLM 接口 — 通过 .env BACKEND 选择后端（默认 openrouter）

用法：
    from llm import chat, make_tool_result_message, MODEL, BACKEND
"""

import os
from dotenv import load_dotenv

load_dotenv()

BACKEND = os.environ.get("BACKEND", "openrouter").lower()

if BACKEND == "claude-code":
    try:
        from llm_claude_code import is_available
        if not is_available():
            raise RuntimeError("Claude Code CLI (claude) not found in PATH")
        from llm_claude_code import chat, make_tool_result_message, MODEL, ChatResult, ToolCall
    except ImportError as e:
        raise RuntimeError(f"Claude Code backend failed: {e}")
else:
    BACKEND = "openrouter"
    try:
        from llm_openrouter import chat, make_tool_result_message, MODEL, ChatResult, ToolCall
    except Exception as e:
        raise RuntimeError(
            f"OpenRouter backend failed: {e}\n"
            f"Check OPENROUTER_API_KEY and MODEL in .env"
        )
