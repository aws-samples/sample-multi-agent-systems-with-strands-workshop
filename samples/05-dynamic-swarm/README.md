# Module 5: Dynamic Swarm

**Pattern 4 from the deck.** Agents hand off autonomously — no fixed path, no orchestrator. The route through the team emerges at runtime based on what each agent decides to do next.

## Architecture

```
Task (brief)
     │
     ▼
┌──────────────┐   SHARED CONTEXT / WORKING MEMORY
│  Researcher  │  ← entry point; uses tools, gathers data
└──────┬───────┘
       │  handoff_to_agent("analyst")   ← autonomous decision
       ▼
┌──────────────┐
│   Analyst    │  ← receives shared context + handoff message
└──────┬───────┘
       │  handoff_to_agent("writer")    ← autonomous decision
       ▼
┌──────────────┐
│    Writer    │  ← writes final memo; decides NOT to hand off
└──────────────┘
```

This path is not programmed — it emerges based on agent descriptions and what each agent decides.

## What you'll build

A 3-agent Swarm (Researcher → Analyst → Writer) where routing is autonomous. No edges are defined — each agent reads the descriptions of its peers and decides who to hand off to.

## Files

| File | Purpose |
|------|---------|
| `module-05.ipynb` | Step-by-step notebook: create agents → build swarm → run → inspect path → metrics |
| `chat.py` | Run the swarm interactively from the terminal |
| `requirements.txt` | `strands-agents>=1.52.0` |

## Key concepts

- `Swarm([agents], entry_point=agent)` — no routing code, agents decide
- `description` field — the routing signal; write it for the model, not for humans
- `handoff_to_agent` — automatically added to each agent by the SDK
- `result.node_history` — the path that emerged at runtime
- `result.results["agent_name"]` — output from a specific agent
- `result.accumulated_usage` — total token usage across all agents

## Strands API

```python
from strands import Agent
from strands.multiagent import Swarm

researcher = Agent(
    name="researcher",
    description="Market research specialist with tools for company data...",
    system_prompt="...",
    tools=[...],
    callback_handler=None,
)
analyst = Agent(name="analyst", description="...", system_prompt="...", callback_handler=None)
writer  = Agent(name="writer",  description="...", system_prompt="...", callback_handler=None)

swarm = Swarm(
    [researcher, analyst, writer],
    entry_point=researcher,
    max_handoffs=6,
    max_iterations=10,
    execution_timeout=180.0,
)
result = swarm(task)

# Access results
path  = [n.node_id for n in result.node_history]
memo  = str(result.results["writer"])
usage = result.accumulated_usage
```

## Swarm vs Sequential Chain

| | Sequential Chain (M2) | Dynamic Swarm (M5) |
|---|---|---|
| Path | Fixed in Python code | Emergent — agents decide |
| Control | Deterministic | Autonomous |
| Change path | Rewrite code | Change `description` |
| Best for | Known, stable workflows | Exploration, multi-domain tasks |

## Run

```bash
pip install -r requirements.txt
python chat.py
```

## Prerequisites

Module 1 — imports tools from `../01-strands-foundations/decision_brief_tools.py`.

## Next

→ [Module 6: Agent-as-Tool (Capstone)](../06-agent-as-tool/)
