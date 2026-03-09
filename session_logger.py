"""
Session Logger — 记录 agent 完整调用过程

每个 task 一个 session，生成独立的 JSON 日志文件。
记录：session 元信息、每轮 LLM 输入/输出、工具调用/结果、模型推理与决策。

日志保存在 logs/ 目录，文件名格式：{timestamp}_{session_id[:8]}.json

用法（在 agent 中只需 ~5 行）：
    from session_logger import SessionLogger

    log = SessionLogger(task, model)
    result = chat(messages, tools=TOOLS)
    log.log_turn(messages, result)
    log.log_tool(tc.name, tc.args, output)
    log.save()
"""

import os, json, time, uuid
from datetime import datetime


class SessionLogger:
    def __init__(self, task: str, model: str):
        self.session_id = uuid.uuid4().hex
        self.model = model
        self.task = task
        self.start_time = time.time()
        self.turns: list[dict] = []
        self._current_turn: dict | None = None

    # ── 每轮调用 ─────────────────────────────────────────────────

    def log_turn(self, messages: list, result) -> None:
        """记录一轮 LLM 调用：输入消息摘要 + 模型输出。"""
        self._current_turn = {
            "turn": len(self.turns) + 1,
            "timestamp": datetime.now().isoformat(),
            "input_message_count": len(messages),
            "last_input": _summarize_message(messages[-1]) if messages else None,
            "output_text": result.text,
            "tool_calls_requested": [
                {"name": tc.name, "args": tc.args} for tc in result.tool_calls
            ],
            "finished": result.finished,
            "tool_executions": [],
        }
        self.turns.append(self._current_turn)

    def log_tool(self, name: str, args: dict, output: str, error: str | None = None) -> None:
        """记录一次工具执行：名称、参数、输出、是否出错。"""
        entry = {
            "tool": name,
            "args": args,
            "output": _truncate(output, 2000),
            "error": error,
        }
        if self._current_turn:
            self._current_turn["tool_executions"].append(entry)

    # ── 保存 ─────────────────────────────────────────────────────

    def save(self) -> str:
        """保存日志到 logs/ 目录，返回文件路径。"""
        elapsed = round(time.time() - self.start_time, 2)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        doc = {
            "session_id": self.session_id,
            "model": self.model,
            "task": self.task,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "elapsed_seconds": elapsed,
            "total_turns": len(self.turns),
            "turns": self.turns,
        }

        os.makedirs("logs", exist_ok=True)
        path = f"logs/{ts}_{self.session_id[:8]}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)

        return path


# ── 内部工具函数 ─────────────────────────────────────────────────

def _truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[:limit] + f"\n... ({len(s)} chars total)"


def _summarize_message(msg) -> dict:
    """提取消息的关键信息，避免日志过大。"""
    if isinstance(msg, dict):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, str):
            return {"role": role, "content": _truncate(content, 500)}
        if isinstance(content, list):
            return {"role": role, "content": f"[{len(content)} blocks]"}
        return {"role": role, "content": str(content)[:200]}
    # OpenAI ChatCompletionMessage object
    return {"role": getattr(msg, "role", "?"), "content": _truncate(str(getattr(msg, "content", "")), 500)}
