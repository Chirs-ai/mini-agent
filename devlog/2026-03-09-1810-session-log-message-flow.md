# Session 日志与 LLM Message 流转机制解析

时间：2026-03-09 18:10

## 背景

基于 `output/20260309_174354_5f23ae96/session.json` 的一次完整 agent 运行记录，深入分析 mini-agent 的 session 日志结构、messages 构建逻辑和 LLM 返回结构。该 session 使用 `anthropic/claude-sonnet-4-6` 模型，5 轮完成了 Collatz 序列 ASCII 可视化任务。

## 1. Session 日志中的两阶段记录

每一轮（turn）包含两个关键字段：

- **`tool_calls_requested`**：LLM 返回的工具调用指令（模型的"意图"）
- **`tool_executions`**：框架实际执行工具后的结果（真实输出 + error）

执行顺序：`tool_calls_requested`（解析自 LLM 响应） → `tool_executions`（框架执行）

分开记录的意义：可以区分 LLM 决策层问题（模型请求了错误的工具/参数）和执行层问题（工具本身运行失败）。

## 2. Messages 数组的构建逻辑

### 初始状态

```python
messages = [
    {"role": "system", "content": SYSTEM},   # 系统提示
    {"role": "user", "content": task},        # 用户任务
]
```

### 每轮追加规则

每轮 LLM 调用后固定追加 2 条消息：
1. `{"role": "assistant", ...}` — LLM 的回复（可能含 content 和/或 tool_calls）
2. `{"role": "tool", "tool_call_id": "...", "content": "..."}` — 工具执行结果

因此 `input_message_count = 2 + (turn - 1) × 2`，本 session 从 2 条增长到 10 条。

### Assistant message 的序列化（`ChatResult.message` 属性）

```python
msg = {"role": "assistant", "content": self.text}
if self.tool_calls:
    msg["tool_calls"] = [
        {"id": tc.id, "type": "function",
         "function": {"name": tc.name, "arguments": json.dumps(tc.args)}}
        for tc in self.tool_calls
    ]
```

关键：`arguments` 是 JSON **字符串**（不是对象），因为 OpenAI 格式要求 `function.arguments` 为字符串。

### Tool result message 的构造

```python
{"role": "tool", "tool_call_id": tool_call_id, "content": output}
```

通过 `tool_call_id` 与 assistant message 中的 `tool_calls[].id` 关联。

## 3. LLM 返回结构的三种情况

本 session 恰好覆盖了所有情况：

### 情况 A：只有 tool_calls，无文本（Turn 1、2、4）

```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [{"id": "...", "type": "function", "function": {"name": "bash", "arguments": "..."}}]
  },
  "finish_reason": "tool_calls"
}
```

解析结果：`ChatResult(text=None, tool_calls=[...])` → `finished = False`，循环继续。

### 情况 B：文本 + tool_calls 同时存在（Turn 3）

```json
{
  "message": {
    "role": "assistant",
    "content": "The 6 random numbers are: ...",
    "tool_calls": [{"id": "...", "type": "function", "function": {"name": "write_file", "arguments": "..."}}]
  },
  "finish_reason": "tool_calls"
}
```

LLM 先输出解释文字，同时请求调用工具。`finished = False`。

### 情况 C：只有文本，无 tool_calls（Turn 5）

```json
{
  "message": {
    "role": "assistant",
    "content": "Everything runs perfectly...",
    "tool_calls": null
  },
  "finish_reason": "stop"
}
```

解析结果：`ChatResult(text="...", tool_calls=[])` → `finished = True`，循环终止。

### 判断循环终止的唯一标准

`tool_calls` 是否为空。`content` 有没有值不影响流程控制。

## 4. 防御性处理：JSON 解析失败兜底

```python
try:
    args = json.loads(tc.function.arguments)
except json.JSONDecodeError:
    args = {"_raw": tc.function.arguments}
```

弱模型可能生成非法 JSON，用 `_raw` 兜底防止 agent 循环崩溃。

## 5. 本 session 的完整 message 流转

```
Turn 1: [system, user]                                          → LLM → bash(python3)     ❌ 报错
Turn 2: [system, user, asst→bash, tool→报错]                     → LLM → bash(python)      ✅ 得到随机数
Turn 3: [... +asst→bash, tool→随机数]                            → LLM → write_file(脚本)  ✅ 写入文件
Turn 4: [... +asst→write_file, tool→OK]                         → LLM → bash(运行脚本)    ✅ ASCII 输出
Turn 5: [... +asst→bash, tool→ASCII输出]                        → LLM → 纯文本总结        🏁 finished
```

## 涉及文件

- `llm_openrouter.py` — LLM 调用与响应解析（`ChatResult`、`ToolCall`、`make_tool_result_message`）
- `mini_agent.py` — agent 循环主体（messages 构建与 turn 记录）
- `output/20260309_174354_5f23ae96/session.json` — 分析对象
