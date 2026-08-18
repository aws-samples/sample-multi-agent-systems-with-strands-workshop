# Module 4: Critic-Refiner

**Pattern 3 from the deck.** Add a quality gate — the Writer drafts the memo, the Critic evaluates it against a checklist, and if the bar is not met the memo cycles back for revision until approved.

## Architecture

```
Decision Brief + Research
          │
          ▼
    ┌───────────┐
    │  Writer   │◄──────────────────────┐
    └─────┬─────┘                       │
          │ draft memo                  │ feedback: REVISION NEEDED
          ▼                             │
    ┌───────────┐  REVISION NEEDED: ───►┘
    │  Critic   │
    └─────┬─────┘
          │ APPROVED
          ▼
    Final memo
```

## What you'll build

A `GraphBuilder` feedback loop: Writer → Critic → [APPROVED: done | REVISION NEEDED: cycle back to Writer].

## Files

| File | Purpose |
|------|---------|
| `module-04.ipynb` | Step-by-step notebook: research → Writer → Critic → graph loop → metrics |
| `chat.py` | Run the critic-refiner pipeline interactively |
| `requirements.txt` | `strands-agents>=1.52.0` |

## Key concepts

- `GraphBuilder` — builds a directed graph of agents with conditional edges
- Cycle edge — `add_edge("critic", "writer", condition=needs_revision)` creates the feedback loop
- `set_entry_point("writer")` — required when a cycle makes the start node ambiguous
- `set_max_node_executions(N)` — safety limit to prevent infinite loops
- `reset_on_revisit(True)` — resets node state on each revisit

## Strands API

```python
from strands import Agent
from strands.multiagent import GraphBuilder

writer = Agent(name="writer", system_prompt=WRITER_PROMPT, callback_handler=None)
critic = Agent(name="critic", system_prompt=CRITIC_PROMPT, callback_handler=None)

def needs_revision(state):
    r = state.results.get("critic")
    return bool(r) and "revision needed" in str(r.result).lower()

builder = GraphBuilder()
builder.add_node(writer, "writer")
builder.add_node(critic, "critic")
builder.set_entry_point("writer")
builder.add_edge("writer", "critic")
builder.add_edge("critic", "writer", condition=needs_revision)
builder.set_max_node_executions(8)
builder.set_execution_timeout(180)
builder.reset_on_revisit(True)

graph = builder.build()
result = graph(brief_with_research)

# Check execution order and critic verdicts
print([n.node_id for n in result.execution_order])
```

## Critic output format — critical design rule

The condition function `needs_revision` parses the Critic's text. The Critic **must** respond with either `APPROVED` or `REVISION NEEDED: ...` — if it writes prose instead, conditions fail silently and the graph either loops forever or exits prematurely. The system prompt must enforce this format.

## Run

```bash
pip install -r requirements.txt
python chat.py
```

## Prerequisites

Module 1 — imports tools from `../01-strands-foundations/decision_brief_tools.py`.

## Next

→ [Module 5: Dynamic Swarm](../05-dynamic-swarm/)
