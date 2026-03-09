# Minimal Agent 架构设计

**时间**：2026-03-09 12:30
**主题**：基于 pi 设计哲学的极简 Python Agent 实现

## 背景

通过阅读两篇文章深入理解了 pi 编码智能体的设计哲学：

- [Armin Ronacher - Pi: The Minimal Agent Within OpenClaw](https://lucumr.pocoo.org/2026/1/31/pi/) (2026-01-31)
- [Mario Zechner - What I learned building an opinionated and minimal coding agent](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) (2025-11-30)

以及 pi 的核心代码实现：[pi-mono/packages/agent](https://github.com/badlogic/pi-mono/tree/main/packages/agent)

目标是用 Python 实现一个极简 Agent 示例，验证核心架构模式。

## pi 的核心设计哲学

### 极简原则

pi 整个 agent 核心只有 5 个 TypeScript 文件：

| 文件 | 职责 |
|------|------|
| `types.ts` | 状态、事件、工具、消息类型定义 |
| `agent.ts` | Agent 类：状态管理 + 事件分发 |
| `agent-loop.ts` | 代理循环：核心交互引擎 |
| `proxy.ts` | 通过后端代理路由 LLM 请求 |
| `index.ts` | 统一导出 |

### 关键架构决策

1. **最小工具集**：只有 4 个工具（read, write, edit, bash），系统提示仅 ~1000 词
2. **双层消息系统**：`AgentMessage[]`（应用层）→ `convertToLlm()` → `Message[]`（LLM 层），扩展可在应用层持久化状态而不污染 LLM 上下文
3. **YOLO 模式**：无权限提示、无安全审批，认为一旦 agent 能执行代码，安全措施大多是"安全剧场"
4. **故意不做的事**：无 MCP、无规划模式、无内置 TODO、无子代理工具、无后台 bash

### 核心循环

```
外层循环：检查 follow-up 消息队列
  └─ 内层循环：LLM 对话轮次
       ├─ streamAssistantResponse() — 流式获取 LLM 回复
       ├─ executeToolCalls() — 执行工具调用
       ├─ 检查 steering 消息 — 支持中途打断
       └─ 工具结果回送 → 继续循环直到 LLM 停止调用工具
```

## 方案设计

### Python 极简实现

将 pi 的核心循环精炼为 ~100 行 Python 代码，核心只有一个 `agent_loop()` 函数：

```
messages = [user: task]

while True:
  ① LLM(messages) → response
  ② stop_reason == "end_turn"? → 结束
  ③ 取出 tool_use blocks
  ④ execute_tool(name, args) → result
  ⑤ 把 tool_result 追加到 messages
  └──→ 回到 ①
```

### 工具集

3 个工具（比 pi 少了 edit，保持最小化）：

- **bash** — 执行 shell 命令
- **write_file** — 写文件（自动创建目录）
- **read_file** — 读文件

### 示例任务

让 agent 做一件"简单但不寻常"的事：探索 Collatz 猜想，随机选 6 个数，计算各自的 Collatz 序列，然后自行编写并运行一个 ASCII 山脉可视化脚本。

这个任务展示了多步工具调用：bash（计算）→ write_file（写脚本）→ bash（运行脚本），清晰体现代理循环的工作方式。

## 产出文件

| 文件 | 说明 |
|------|------|
| `mini_agent.py` | 完整的极简 Agent 实现 |
| `CLAUDE.md` | 项目说明 |
| `.gitignore` | Git 忽略配置 |

## 后续方向

- 添加流式输出（streaming）支持
- 添加 edit 工具（精确文本替换）
- 添加 `transformContext()` 上下文裁剪钩子
- 添加事件系统（agent_start, tool_execution_start 等）
- 实际运行测试（需设置 ANTHROPIC_API_KEY）
