# mini-agent

A minimal coding agent in ~160 lines of Python, inspired by [pi](https://github.com/badlogic/pi-mono).

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
├── mini_agent.py        # Agent core — loop + 4 tools (~160 lines)
├── llm.py               # Unified LLM interface (auto-selects backend)
├── llm_claude_code.py   # Claude Code CLI backend (delegate mode)
├── llm_openrouter.py    # OpenRouter API backend (OpenAI-compatible)
├── session_logger.py    # Session logging (JSON, per-task)
├── tasks/               # Predefined task files
├── .env.example         # Config template
├── output/              # Auto-generated session logs + task outputs
└── devlog/              # Design documents
```

### Files

| File | Lines | Purpose |
|------|-------|---------|
| `mini_agent.py` | ~170 | Agent loop + tool definitions (bash, write_file, read_file, edit) |
| `llm.py` | ~30 | Unified entry point — Claude Code CLI first, OpenRouter fallback |
| `llm_claude_code.py` | ~100 | Delegate entire task to `claude -p` (CC handles agent loop internally) |
| `llm_openrouter.py` | ~135 | OpenRouter client with standardized `ChatResult` / `ToolCall` types |
| `session_logger.py` | ~105 | Per-session JSON logger, plugs into agent with ~5 lines |

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd mini-agent

# 2. Install dependencies
pip install openai python-dotenv

# 3. Run (auto-selects Claude Code CLI if available, otherwise OpenRouter)
python mini_agent.py tasks/collatz.txt          # from task file
python mini_agent.py "write a hello world"      # inline task
python mini_agent.py                            # interactive prompt
```

## LLM Backends

The agent auto-selects the best available backend:

| Priority | Backend | How it works | Cost |
|----------|---------|-------------|------|
| 1st | **Claude Code CLI** | Delegates to `claude -p` (CC runs its own agent loop) | CC subscription |
| 2nd | **OpenRouter API** | Our agent loop with tool calling | API pay-per-use |

### Claude Code CLI (auto-detected)

If `claude` is in your PATH, it's used automatically. No configuration needed.

### OpenRouter (fallback)

```bash
cp .env.example .env    # fill in your key and model
```

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

The agent has 4 tools — the same set as [pi](https://github.com/badlogic/pi-mono):

| Tool | Description |
|------|-------------|
| `bash` | Run a shell command, return stdout+stderr |
| `write_file` | Create or overwrite a file (auto-creates directories) |
| `read_file` | Read a file and return its content |
| `edit` | Replace an exact substring in a file (must be unique match) |

## Session Logging

Every run generates a JSON log in `output/`, recording:

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

## Example Tasks

### Collatz ASCII Art (`tasks/collatz.txt`)

Compute Collatz sequences for random numbers, visualize as overlapping ASCII mountain ranges:

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
```

### CLI Task Manager (`tasks/task_manager.txt`)

Build a task manager, test it, then **edit** (not rewrite) to add priority + stats — 28 turns, 31/31 tests pass:

```
$ python task_app.py add "Fix critical bug" --priority high
Added task #1 [high]: Fix critical bug

$ python task_app.py stats
=== Task Statistics ===
  Total   : 5
  Done    : 2
  Pending : 3
  Progress: [############------------------] 40.0%
  High    : 1/2 done
  Medium  : 1/1 done
  Low     : 0/2 done
```

The agent used `edit` 7 times to surgically add features to existing code without rewriting the file.

## Design Philosophy

This project demonstrates that a useful coding agent needs very little infrastructure:

1. **Minimal core** — One loop, four tools, zero abstractions
2. **Model does the thinking** — No planner, no state machine; the LLM decides what to do next
3. **Self-correction** — Errors from tool execution feed back as context; the model adapts
4. **Dual backend** — Claude Code CLI (free) with automatic OpenRouter fallback
5. **Observable** — Session logs capture every decision for analysis and comparison

Inspired by [pi](https://github.com/badlogic/pi-mono) by Mario Zechner and the philosophy described in:
- [What I learned building an opinionated and minimal coding agent](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)
- [Pi: The Minimal Agent Within OpenClaw](https://lucumr.pocoo.org/2026/1/31/pi/) by Armin Ronacher

## License

MIT
