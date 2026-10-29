# Module 2: Single Agent

Build a Decision Intelligence agent with tools, run it, and inspect the agentic loop. Understand the single-agent ceiling before moving to multi-agent patterns.

## What you'll build

A single agent with three mock business intelligence tools that can look up company data, market benchmarks, and competitor information to support strategic decisions.

## Files

| File | Purpose |
|------|---------|
| `module-02.ipynb` | Step-by-step notebook: tools → agent → loop inspection → ceiling demo |
| `chat.py` | Interactive multi-turn chat with the notebook's Strategy Advisor agent |
| `decision_brief_tools.py` | Three mock `@tool` functions + MarketNest mock data |
| `requirements.txt` | `strands-agents>=1.52.0` |

## Architecture

![Single Agent: Decision Brief flows into the AGENT (Planning, Research, Analysis, Writing) producing the Decision Memo](./single-agent.png)

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

`chat.py` runs the Strategy Advisor from the notebook's main path (same system prompt and model) and waits for you to type or paste a situation. A multi-line text pasted at once (like `SITUATION_SUMMARY` in the notebook) is sent as one message. The chat keeps ONE `Agent` for the whole session, so follow-up questions build on earlier answers; `context_manager="auto"` keeps that growing history within the model's context window. Type `quit` (or press Ctrl+C) to exit.

## Model options

The notebook and `chat.py` pin `us.anthropic.claude-sonnet-4-5-20250929-v1:0`. To switch, change the `model_id` in `BedrockModel(model_id="...")`, for example:

- `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- `amazon.nova-pro-v1:0`
- `amazon.nova-lite-v1:0`

Use a model that is enabled in your account and Region.

## Next

→ [Module 3: Sequential Chain](../03-sequential-chain/)
