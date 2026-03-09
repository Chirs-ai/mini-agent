"""
统一 LLM 接口 — 优先 Claude Code CLI，回退 OpenRouter API

用法：
    from llm import chat, make_tool_result_message, MODEL, BACKEND
"""

BACKEND = None

# 优先尝试 Claude Code CLI
try:
    from llm_claude_code import is_available
    if is_available():
        from llm_claude_code import chat, make_tool_result_message, MODEL, ChatResult, ToolCall
        BACKEND = "claude-code"
except Exception:
    pass

# 回退到 OpenRouter API
if BACKEND is None:
    try:
        from llm_openrouter import chat, make_tool_result_message, MODEL, ChatResult, ToolCall
        BACKEND = "openrouter"
    except Exception as e:
        raise RuntimeError(
            f"No LLM backend available.\n"
            f"  - Claude Code CLI: not found in PATH\n"
            f"  - OpenRouter: {e}\n"
            f"Install Claude Code (npm i -g @anthropic-ai/claude-code) or set OPENROUTER_API_KEY in .env"
        )
