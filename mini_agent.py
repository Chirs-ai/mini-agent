"""
Minimal Agent — 用 ~80 行 Python 演示 pi 的核心架构

核心循环：
    messages[] → LLM → tool_calls? → execute → append results → repeat

就这么简单。没有规划模式、没有子代理、没有 MCP，只有循环。

用法：
    1. cp .env.example .env  # 填入 OpenRouter key 和模型
    2. pip install openai python-dotenv
    3. python mini_agent.py
"""

import json, subprocess, os, sys
from llm import chat, make_tool_result_message, MODEL, BACKEND
from session_logger import SessionLogger

sys.stdout.reconfigure(encoding="utf-8")

# ── 工具定义（与 pi 相同的 4 个：read/write/edit/bash） ──────────

TOOLS = [
    {
        "name": "bash",
        "description": "Run a bash command, return stdout+stderr.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file with the given content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file and return its content.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "edit",
        "description": "Replace an exact substring in a file. old_text must match exactly (including whitespace/indentation). Fails if old_text is not found or matches multiple locations — provide more surrounding context to make it unique.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to edit"},
                "old_text": {"type": "string", "description": "Exact text to find (must be unique in file)"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    """执行一个工具调用，返回文本结果。"""
    if name == "bash":
        r = subprocess.run(
            args["command"], shell=True, capture_output=True, text=True, timeout=30
        )
        return (r.stdout + r.stderr).strip() or "(no output)"
    elif name == "write_file":
        os.makedirs(os.path.dirname(args["path"]) or ".", exist_ok=True)
        with open(args["path"], "w", encoding="utf-8") as f:
            f.write(args["content"])
        return f"OK, written to {args['path']}"
    elif name == "read_file":
        with open(args["path"], encoding="utf-8") as f:
            return f.read()
    elif name == "edit":
        path, old, new = args["path"], args["old_text"], args["new_text"]
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        count = content.count(old)
        if count == 0:
            return f"Error: old_text not found in {path}"
        if count > 1:
            return f"Error: old_text matches {count} locations in {path}. Provide more context to make it unique."
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.replace(old, new, 1))
        return f"OK, edited {path}"
    return "Unknown tool"


# ── 代理循环（这就是全部核心） ───────────────────────────────────

SYSTEM = "You are a minimal coding agent with bash, write_file, read_file, edit tools. Prefer edit over write_file for modifying existing files. Be concise. Accomplish the task step by step."


def agent_loop(task: str):
    print(f"\n{'='*60}\n  TASK: {task}\n  MODEL: {MODEL} ({BACKEND})\n{'='*60}")

    log = SessionLogger(task, MODEL)                            # +1

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    turn = 0

    while True:
        turn += 1
        print(f"\n── turn {turn} ──")

        # 1) 调用 LLM（通过 OpenRouter）
        result = chat(messages, tools=TOOLS)
        log.log_turn(messages, result)                          # +2

        # 2) 打印文本输出
        if result.text:
            print(f"\n{result.text}")

        # 3) 没有工具调用 → 结束
        if result.finished:
            path = log.save()                                   # +3
            print(f"\n{'='*60}\n  DONE ({turn} turns) | log: {path}\n{'='*60}")
            return

        # 4) 执行所有工具调用，收集结果
        #    先把 assistant 消息（含 tool_calls）追加到历史
        messages.append(result.message)

        for tc in result.tool_calls:
            print(f"\n  > {tc.name}({json.dumps(tc.args, ensure_ascii=False)[:120]})")
            try:
                output = execute_tool(tc.name, tc.args)
                log.log_tool(tc.name, tc.args, output)          # +4
            except Exception as e:
                output = f"Error: {e}"
                log.log_tool(tc.name, tc.args, output, error=str(e))  # +5
            if len(output) > 8000:
                output = output[:8000] + "\n... (truncated)"
            print(f"    {output[:300]}")

            # 5) 每个工具结果作为独立 tool message 追加
            messages.append(make_tool_result_message(tc.id, output))

        # → 回到步骤 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        with open(sys.argv[1], encoding="utf-8") as f:
            task = f.read().strip()
    elif len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = input("Task: ")
    agent_loop(task)
