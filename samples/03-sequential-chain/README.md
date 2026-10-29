# Module 3: Sequential Chain

**Pattern 1.** Break the single-agent ceiling with a 3-stage pipeline where each agent has one focused job and passes its output to the next.

**Strands primitive:** `GraphBuilder` (Graph)

## Architecture

![Sequential Chain: Decision Brief → Researcher → Analyst → Synthesizer → Leadership Memo](./architecture.png)

## What you'll build

A 3-stage pipeline — Researcher → Analyst → Synthesizer — defined as a directed graph.
Each node's output is automatically passed as input to the next node by the graph engine.
Each agent has a narrow system prompt and sees only what it needs for its role.

## Files

| File | Purpose |
|------|---------|
| `module-03.ipynb` | Step-by-step notebook: prompts → GraphBuilder → run → inspect |
| `chat.py` | Run the same chain interactively, with conversation memory across turns |
| `requirements.txt` | `strands-agents>=1.52.0` |
| `production/` | Deploy specialists to AgentCore Runtime; coordinate via `chain.py` |

## Key concepts

- **GraphBuilder**: Strands primitive for deterministic multi-agent graphs (a directed acyclic graph of agents)
- **`add_node` / `add_edge`**: declare the graph structure; the engine enforces execution order
- **Output propagation**: each node's output is automatically passed as input to connected nodes
- **`callback_handler=None`**: silent intermediate agents; display the final result explicitly
- **Focused context**: no single agent holds everything — each sees only its stage's inputs

## Strands GraphBuilder

```python
from strands import Agent
from strands.multiagent import GraphBuilder

researcher  = Agent(system_prompt=RESEARCHER_PROMPT,  callback_handler=None)
analyst     = Agent(system_prompt=ANALYST_PROMPT,     callback_handler=None)
synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)

builder = GraphBuilder()
builder.add_node(researcher,  "researcher")
builder.add_node(analyst,     "analyst")
builder.add_node(synthesizer, "synthesizer")
builder.add_edge("researcher", "analyst")
builder.add_edge("analyst",    "synthesizer")

result = builder.build()(brief)

# Extract the final node's output
for node in reversed(result.execution_order):
    if node.node_id == "synthesizer":
        print(str(node.result))
        break
```

See the [Strands GraphBuilder docs](https://strandsagents.com/docs/user-guide/sdk/multi-agent/graph/) and [multi-agent patterns](https://strandsagents.com/docs/user-guide/sdk/multi-agent/multi-agent-patterns/).

**Pricing:**
- [Amazon Bedrock model pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon Bedrock AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)

## Prerequisites

- Python 3.10 or higher
- Module 2: this module imports tools from `../02-single-agent/decision_brief_tools.py`

## Run

```bash
uv pip install -r requirements.txt
uv run python chat.py
```

## Chat and conversation memory

`chat.py` runs the same graph as the notebook (same prompts, agents, edges and timeout) and waits for you to type or paste a brief. A multi-line brief pasted at once (like `DECISION_BRIEF` in the notebook) is sent as one message. Ask follow-ups in the same session; type `quit` (or press Ctrl+C) to exit.

Every turn builds the graph fresh, exactly like the notebook. The conversation is remembered with [Strands memory](https://strandsagents.com/docs/user-guide/sdk/memory/overview/):

- One in-memory [`TestMemoryStore`](https://strandsagents.com/docs/user-guide/sdk/memory/test-memory-store/) (`persist=False`, nothing is written to disk) stores only two entries per turn: what you said and the final answer (the synthesizer's memo). Nothing the agents say to each other is stored.
- Every agent gets its own `MemoryManager` over that store. [Context injection](https://strandsagents.com/docs/user-guide/sdk/memory/managing-memory/) adds the relevant entries to the agent's model input before each call. `search_tool_config=False` keeps each agent's tools the same as in the notebook.
- Inside a turn the agents still pass work to each other only through the graph edges.

`TestMemoryStore` uses keyword matching and is meant for prototyping. For production, use a managed store such as the [Bedrock Knowledge Base store](https://strandsagents.com/docs/user-guide/sdk/memory/bedrock-knowledge-base/).

## Next

→ [Module 4: Parallel Fork-Join](../04-parallel-fork-join/)
