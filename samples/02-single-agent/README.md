# Module 2: Single Agent

Build a Decision Intelligence agent with tools, run it, and inspect the agentic loop. Understand the single-agent ceiling before moving to multi-agent patterns.

## What you'll build

A single agent with three mock business intelligence tools that can look up company data, market benchmarks, and competitor information to support strategic decisions.

## Files

| File | Purpose |
|------|---------|
| `module-02.ipynb` | Step-by-step notebook: tools → agent → loop inspection → ceiling demo |
| `chat.py` | Interactive multi-turn chat in the terminal |
| `decision_brief_tools.py` | Three mock `@tool` functions + NovaCart mock data |
| `requirements.txt` | `strands-agents>=1.52.0` |

## How the Agentic Loop Works

![Strands agentic loop: Input & Context → Reasoning LLM → Tool Selection → Tool Execution → cycle back → Response](./agent-loop.png)

## Key concepts

- `@tool` decorator: Python function the LLM can call; docstring is the routing logic
- `Agent(tools=[], system_prompt=...)`: assembles the harness
- `agent.messages`: full conversation history (user turns, LLM responses, tool calls, tool results)
- `result.metrics.get_summary()`: token usage, cycle count, per-tool stats
- The ceiling: why a single agent struggles with complex, multi-dimensional tasks

## Prerequisites

- Python 3.10 or higher

## Run

```bash
uv pip install -r requirements.txt
uv run python chat.py
```

Or open `module-02.ipynb` in VS Code / JupyterLab and run cells top to bottom.

## Model options

Pass `model=BedrockModel(model_id="...")` to `Agent(...)` to switch models:

- `us.anthropic.claude-sonnet-4-20250514-v1:0` (default)
- `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- `amazon.nova-pro-v1:0`
- `amazon.nova-lite-v1:0`

## Next

→ [Module 3: Sequential Chain](../03-sequential-chain/)
