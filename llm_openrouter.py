"""
OpenRouter LLM 调用接口

统一封装 OpenRouter API，返回与具体 SDK 无关的标准化结果。
支持通过 .env 配置 key 和模型，可调用任意 LLM（Claude, GPT, Gemini, DeepSeek ...）

用法：
    from llm_openrouter import chat, TOOLS_OPENAI

    result = chat(messages, tools=TOOLS_OPENAI)
    print(result.text)           # 文本回复
    print(result.tool_calls)     # [ToolCall(id, name, args), ...]
    print(result.finished)       # True = 没有工具调用，对话结束
"""

import os, json
from dataclasses import dataclass, field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── 配置 ─────────────────────────────────────────────────────────

API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = os.environ.get("MODEL", "anthropic/claude-sonnet-4")

_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)


# ── 标准化结果 ───────────────────────────────────────────────────

@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ChatResult:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: object = None  # 原始响应，调试用

    @property
    def finished(self) -> bool:
        """没有工具调用 = 对话结束"""
        return len(self.tool_calls) == 0


# ── 工具格式转换 ─────────────────────────────────────────────────

def to_openai_tools(tools: list[dict]) -> list[dict]:
    """将 Anthropic 格式的工具定义转为 OpenAI function calling 格式。

    Anthropic:  {"name": ..., "description": ..., "input_schema": {...}}
    OpenAI:     {"type": "function", "function": {"name": ..., "parameters": {...}}}

    如果已经是 OpenAI 格式（有 "type": "function"），原样返回。
    """
    result = []
    for t in tools:
        if t.get("type") == "function":
            result.append(t)
        else:
            result.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", t.get("parameters", {})),
                },
            })
    return result


def make_tool_result_message(tool_call_id: str, content: str) -> dict:
    """构造工具结果消息（OpenAI 格式）。"""
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


# ── 核心调用 ─────────────────────────────────────────────────────

def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
) -> ChatResult:
    """调用 OpenRouter，返回标准化的 ChatResult。

    Args:
        messages:   OpenAI 格式的消息列表
        tools:      工具定义（支持 Anthropic 或 OpenAI 格式，自动转换）
        model:      模型 ID（默认用 .env 中的 MODEL）
        max_tokens: 最大输出 token 数
    """
    kwargs = {
        "model": model or MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = to_openai_tools(tools)

    resp = _client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message

    # 解析工具调用
    calls = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            calls.append(ToolCall(
                id=tc.id,
                name=tc.function.name,
                args=json.loads(tc.function.arguments),
            ))

    return ChatResult(text=msg.content, tool_calls=calls, raw=resp)
