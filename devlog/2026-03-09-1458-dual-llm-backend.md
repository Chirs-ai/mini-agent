# Dual LLM Backend：Claude Code CLI + OpenRouter 回退

**时间**：2026-03-09 14:58
**版本**：v0.2.0 → v0.3.0

## 背景

mini-agent v0.2.0 通过 OpenRouter API 调用 LLM，需要 API key 且按量计费。用户希望优先使用已有的 Claude Code CLI 订阅（免费/已付费），仅在 CC 不可用时回退到 OpenRouter。

## 调查过程

### 方案探索

最初设想将 `claude -p` 当作纯文本 LLM，通过 `<tool_call>` 标签格式实现 prompt-based tool calling。但调查发现：

1. **`claude -p` 是完整 agent** — 自带 Bash/Read/Write/Edit/Glob/Grep 等工具，有自己的 system prompt
2. **无法禁用内置工具** — `--allowedTools ""` 和 `--disallowedTools "..."` 均无效，工具始终加载在模型上下文中
3. **模型不遵循自定义 tool format** — CC 的系统提示优先级高于我们的 `<tool_call>` 指令，模型直接使用内置工具

### Windows 环境问题

在实现过程中遇到多个 Windows 特有问题：

| 问题 | 原因 | 解决 |
|------|------|------|
| `FileNotFoundError` | `claude` 是 `.cmd` 文件，subprocess 默认不识别 | 添加 `shell=True` |
| `CLAUDECODE=1` 阻止嵌套 | CC 检测到在 CC 会话内运行 | `env.pop("CLAUDECODE", None)` |
| `git-bash not found` | 清除 env 后丢失 bash 路径 | 自动探测并设置 `CLAUDE_CODE_GIT_BASH_PATH` |
| `gbk codec` 编码错误 | Windows subprocess 默认 GBK | 添加 `encoding="utf-8", errors="replace"` |

## 最终方案：委托模式

放弃"纯 LLM"思路，采用**委托模式**：CC 本身就是 coding agent，直接让它执行整个任务。

### 架构

```
mini_agent.py
  └─ from llm import chat
       └─ llm.py (统一入口)
            ├─ claude-code (优先)：委托 claude -p 执行整个任务，1 turn 完成
            └─ openrouter (回退)：我们的 agent loop，多 turn 循环
```

### 两种模式对比

| | Claude Code | OpenRouter |
|---|---|---|
| 工具来源 | CC 内置 | 我们定义的 4 个 |
| Agent 循环 | CC 内部处理 | 我们的 while 循环 |
| 可观察性 | 仅最终结果 | 每轮 turn 可见 |
| 成本 | CC 订阅 | API 按量计费 |
| 模型 | CC 当前模型 | .env 任意模型 |

### 关键设计决策

1. **`result.message` 属性** — 两个后端的 ChatResult 都提供统一的 `message` 属性返回可序列化 dict，agent 不再依赖 `result.raw.choices[0].message`（OpenAI 特有）
2. **延迟报错** — `llm_openrouter.py` 在 import 时不崩溃（`os.environ.get` 代替 `os.environ[]`），而是抛 ImportError 让 `llm.py` 捕获
3. **错误提示** — 两个后端都不可用时，`llm.py` 给出清晰的安装/配置指引

## 涉及文件

| 文件 | 变更 |
|------|------|
| `llm_claude_code.py` | **新增** — CC CLI 封装（委托模式 + Windows 兼容） |
| `llm.py` | **新增** — 统一入口，CC 优先 + OpenRouter 回退 |
| `llm_openrouter.py` | ChatResult 添加 `message` 属性；API key 延迟报错 |
| `mini_agent.py` | `from llm import ...`；`result.message` 代替 `result.raw.choices[0].message`；显示 BACKEND |
| `.gitignore` | 添加 agent 生成的临时文件 |

## 遗留问题

- CC 委托模式下 session_logger 只记录 1 turn，丢失中间步骤的可观察性
- CC 的 `--output-format json` 返回的 `result` 仅含最终文本，不含中间 tool 调用详情
- 可考虑 `--output-format stream-json` 获取逐事件流式输出以提升可观察性
