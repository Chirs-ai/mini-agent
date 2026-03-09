"""
Claude Code CLI 调用接口

委托模式：claude -p 本身就是完整的 coding agent（自带 bash/read/write/edit），
直接将任务交给它执行，无需我们自己的 tool calling 循环。

当 chat() 被调用时，整个任务一次性交给 CC 处理，返回最终结果（finished=True）。
agent_loop 在第一轮就结束。
"""

import subprocess, json, shutil, os
from dataclasses import dataclass, field

MODEL = "claude-code"


def is_available() -> bool:
    return shutil.which("claude") is not None


# ── 标准化结果（与 llm_openrouter 共享相同接口） ─────────────────

@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ChatResult:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: object = None

    @property
    def finished(self) -> bool:
        return len(self.tool_calls) == 0

    @property
    def message(self) -> dict:
        return {"role": "assistant", "content": self.text}


def make_tool_result_message(tool_call_id: str, content: str) -> dict:
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


# ── 核心调用 ─────────────────────────────────────────────────────

def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    **kwargs,
) -> ChatResult:
    """将任务委托给 claude -p 执行。

    CC 内部运行完整的 agent loop（含多轮 tool calling），
    这里只返回最终结果，tool_calls 为空（finished=True）。
    """
    # 提取用户任务（最后一条 user 消息）
    task = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                task = content
                break

    if not task:
        return ChatResult(text="No task found in messages.", raw=None)

    # 构建环境
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    if os.name == "nt" and not env.get("CLAUDE_CODE_GIT_BASH_PATH"):
        for p in [r"C:\Program Files\Git\bin\bash.exe",
                  r"D:\Program Files\Git\bin\bash.exe"]:
            if os.path.isfile(p):
                env["CLAUDE_CODE_GIT_BASH_PATH"] = p
                break

    proc = subprocess.run(
        "claude -p --output-format json --dangerously-skip-permissions",
        input=task, capture_output=True, text=True, timeout=600,
        shell=True, env=env, encoding="utf-8", errors="replace",
    )

    if proc.returncode != 0:
        err = proc.stderr.strip()[:300] if proc.stderr else "unknown error"
        return ChatResult(text=f"Claude Code error: {err}", raw=None)

    try:
        response = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return ChatResult(text=proc.stdout[:2000] if proc.stdout else "No output", raw=None)

    result_text = response.get("result", "")
    return ChatResult(text=result_text, tool_calls=[], raw=response)
