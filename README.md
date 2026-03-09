# mini-agent

A minimal coding agent in ~100 lines of Python, inspired by [pi](https://github.com/badlogic/pi-mono).

## Core Idea

The entire agent is a single while loop:

```
messages[] → LLM → tool_calls? → execute → append results → repeat
```

No planner, no sub-agents, no MCP, no permission system. The model is smart enough — the framework just faithfully executes tools and passes results back.

```
┌─────────────────────────────────────────┐
│  messages = [user: task]                │
│                                         │
│  while True:                            │
│    ① LLM(messages) → response           │
│    ② stop_reason == "end_turn"? → 结束  │
│    ③ 取出 tool_calls                    │
│    ④ execute_tool(name, args) → result  │
│    ⑤ 把 tool_result 追加到 messages     │
│    └──→ 回到 ①                          │
└─────────────────────────────────────────┘
```

## Project Structure

```
mini-agent/
├── mini_agent.py        # Agent core — loop + 3 tools (~100 lines)
├── llm_openrouter.py    # OpenRouter API wrapper (OpenAI-compatible)
├── session_logger.py    # Session logging (JSON, per-task)
├── .env.example         # Config template
├── logs/                # Auto-generated session logs
└── devlog/              # Design documents
```

### Files

| File | Lines | Purpose |
|------|-------|---------|
| `mini_agent.py` | ~140 | Agent loop + tool definitions (bash, write_file, read_file) |
| `llm_openrouter.py` | ~120 | OpenRouter client with standardized `ChatResult` / `ToolCall` types |
| `session_logger.py` | ~100 | Per-session JSON logger, plugs into agent with ~5 lines |

## Quick Start

```bash
# 1. Clone and configure
git clone <repo-url> && cd mini-agent
cp .env.example .env    # fill in your OpenRouter API key and model

# 2. Install dependencies
pip install openai python-dotenv

# 3. Run
python mini_agent.py
```

## Configuration

Edit `.env`:

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
MODEL=anthropic/claude-sonnet-4         # any OpenRouter model ID
```

Supported models (via [OpenRouter](https://openrouter.ai/models)):

| Model | ID |
|-------|-----|
| Claude Sonnet 4 | `anthropic/claude-sonnet-4` |
| Claude Haiku 3 | `anthropic/claude-3-haiku` |
| GPT-4o | `openai/gpt-4o` |
| Gemini 2.5 Flash | `google/gemini-2.5-flash` |
| DeepSeek V3 | `deepseek/deepseek-chat-v3-0324` |

## Tools

The agent has 3 tools (inspired by pi's minimal 4-tool set):

| Tool | Description |
|------|-------------|
| `bash` | Run a shell command, return stdout+stderr |
| `write_file` | Write content to a file (auto-creates directories) |
| `read_file` | Read a file and return its content |

## Session Logging

Every run generates a JSON log in `logs/`, recording:

- Session ID, model, task, elapsed time
- Each turn: LLM input summary, output text, tool calls requested
- Each tool execution: name, args, output, errors

```json
{
  "session_id": "3d351494...",
  "model": "anthropic/claude-sonnet-4.6",
  "task": "...",
  "elapsed_seconds": 45.3,
  "total_turns": 18,
  "turns": [
    {
      "turn": 1,
      "output_text": "Let me start by...",
      "tool_calls_requested": [{"name": "bash", "args": {"command": "..."}}],
      "tool_executions": [{"tool": "bash", "output": "...", "error": null}]
    }
  ]
}
```

## Example Output

Default task: compute Collatz sequences for 6 random numbers, visualize as ASCII mountain ranges.

```
***  COLLATZ SEQUENCE MOUNTAIN RANGES  ***
+--------------------------------------------------------------------------------+
|               @@                                                               |
|               @@                         *                                     |
|            @  @@                     *   *                                     |
|      #     @  @@                 *   *   *                                     |
|    %#*  @  @  @@@ %             **   * * *                                     |
|  # %@%  @  *@@@@@%% %    @@   * *** ******                                     |
|%*%~~%%%%%%%%*%%*%%~~%%*@~~~*@*************** *   *%  #  %                      |
|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ |
+--------------------------------------------------------------------------------+

  LEGEND:
  Char   Start n   Steps     Peak value
  #         6619     137         50,272
  @         6239      49         94,768
  *         3279     105         95,956
  %         9822     122         59,776
  +         2930      35          4,948
  ~         3773      38         11,320
```

## Design Philosophy

This project demonstrates that a useful coding agent needs very little infrastructure:

1. **Minimal core** — One loop, three tools, zero abstractions
2. **Model does the thinking** — No planner, no state machine; the LLM decides what to do next
3. **Self-correction** — Errors from tool execution feed back as context; the model adapts
4. **Swappable LLM** — Change one line in `.env` to switch between any model
5. **Observable** — Session logs capture every decision for analysis and comparison

Inspired by [pi](https://github.com/badlogic/pi-mono) by Mario Zechner and the philosophy described in:
- [What I learned building an opinionated and minimal coding agent](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)
- [Pi: The Minimal Agent Within OpenClaw](https://lucumr.pocoo.org/2026/1/31/pi/) by Armin Ronacher

## License

MIT
