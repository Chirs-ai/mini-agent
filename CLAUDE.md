# mini-agent

Minimal coding agent in Python, inspired by [pi](https://github.com/badlogic/pi-mono).

## Core Idea

The entire agent is a single while loop:

```
LLM(messages) → tool calls → execute → append results → repeat
```

No planner, no sub-agents, no MCP. The model is smart enough; the framework just faithfully executes tools and passes results back.

## Structure

- `mini_agent.py` — Original minimal agent demo (Anthropic SDK, ~100 lines)
- `llm_openrouter.py` — OpenRouter LLM call interface (OpenAI-compatible, supports any model)
- `.env.example` — Config template for OpenRouter key and model

## Running

```bash
# Original demo (requires ANTHROPIC_API_KEY)
python mini_agent.py

# Using OpenRouter interface
cp .env.example .env   # fill in your key and model
pip install openai python-dotenv
python -c "from llm_openrouter import chat; print(chat([{'role':'user','content':'hi'}]).text)"
```

## Dependencies

- `anthropic` — for mini_agent.py
- `openai` + `python-dotenv` — for llm_openrouter.py
