# Module 6: Agent-as-Tool

**Pattern 5.** Wrap specialized agents as callable tools so an LLM orchestrator can delegate like a manager to experts — routing decided by the model, not by Python code.

## Architecture

```
Decision Brief
       │
       ▼
┌──────────────────────────────────────────┐
│             ORCHESTRATOR                 │
│  tools = [researcher_agent,              │
│            analyzer_agent,               │
│            synthesizer_agent]            │
└───────────┬──────────────────────────────┘
            │ LLM decides: who, when, what parameters
            │
    ┌───────┼──────────┬──────────────┐
    ▼       ▼          ▼              ▼
researcher analyzer_A  analyzer_B  synthesizer
 @tool      @tool       @tool       @tool
 Agent(...)  Agent(...)  Agent(...)  Agent(...)
 silent     silent      silent      streams
```

## What you'll build

An LLM orchestrator that uses three specialist agents as tools. The model decides: call researcher first → call analyzer for each option → call synthesizer. No Python routing code.

## Files

| File | Purpose |
|------|---------|
| `module-06.ipynb` | Step-by-step: prompts → wrap tools → orchestrator → inspect calls → metrics |
| `chat.py` | Run the orchestrator interactively |
| `requirements.txt` | `strands-agents>=1.52.0` |

## Key concepts

- `@tool` wrapping `Agent` — full control over parameters; docstring is the routing logic
- `callback_handler=None` — silent sub-agents; only orchestrator + final synthesizer stream
- LLM routing — the orchestrator decides tool call order and arguments
- Multi-parameter `@tool` — lets the orchestrator pass precise context per call

## Three ways to use Agents as Tools

```python
# Option A — @tool decorator (most control, multi-parameter) — used in this module
@tool
def researcher_agent(topic: str) -> str:
    """Research market context..."""
    worker = Agent(tools=[...], system_prompt=..., callback_handler=None)
    return str(worker(topic))

# Option B — pass Agent directly in tools[] (simplest, single string input)
researcher = Agent(system_prompt=..., tools=[...])
orchestrator = Agent(tools=[researcher, analyst, writer])

# Option C — .as_tool() (custom name/description, optional preserve_context)
orchestrator = Agent(tools=[researcher.as_tool(name="...", description="...")])
```

## Strands API

```python
from strands import Agent, tool

@tool
def researcher_agent(topic: str) -> str:
    """Research market context... (orchestrator reads this docstring)
    Args:
        topic: The decision topic to research
    """
    worker = Agent(tools=[...], system_prompt=RESEARCHER_PROMPT, callback_handler=None)
    return str(worker(topic))

orchestrator = Agent(
    tools=[researcher_agent, analyzer_agent, synthesizer_agent],
    system_prompt=ORCHESTRATOR_PROMPT,
)
result = orchestrator(DECISION_BRIEF)

# Inspect tool calls
for msg in orchestrator.messages:
    for block in msg.get("content", []):
        if "toolUse" in block:
            print(block["toolUse"]["name"])
```

## Run

```bash
pip install -r requirements.txt
python chat.py
```

## Prerequisites

Module 1 — imports tools from `../01-strands-foundations/decision_brief_tools.py`.

## Next

→ [Module 7: Capstone — Decision-Memo System](../07-capstone/)
