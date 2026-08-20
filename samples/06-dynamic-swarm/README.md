# Module 6: Dynamic Swarm

**Pattern 4.** Agents hand off autonomously — no fixed path, no orchestrator. The route through the team emerges at runtime based on what each agent decides to do next.

**Strands primitive:** `Swarm`

## Architecture

![Dynamic Swarm: Monitor, Network Specialist, DB Admin, Resolver — autonomous handoffs, no fixed routing](./architecture.png)

```
Incident Report
      │
      ▼
┌──────────────┐   SHARED CONTEXT / WORKING MEMORY
│   Monitor    │  ← entry point; triages, classifies, routes
└──────┬───────┘
       │  handoff_to_agent("network_specialist" | "db_admin")  ← autonomous
       ▼
┌───────────────────┐      ┌──────────────┐
│ Network Specialist│  ←→  │   DB Admin   │  ← specialists may hand off to each other
└───────────────────┘      └──────────────┘
       │  handoff_to_agent("resolver")            ← autonomous
       ▼
┌──────────────┐
│   Resolver   │  ← synthesizes findings, produces resolution plan
└──────────────┘
```

The path is not programmed — it emerges based on agent `description` fields and what each agent decides.

## What you'll build

A 4-agent Swarm for **IT incident response**. The route adapts to the incident:
- Network issue → `monitor → network_specialist → resolver`
- DB issue → `monitor → db_admin → resolver`
- Mixed → `monitor → network_specialist → db_admin → resolver`

No edges are defined. Each agent reads its peers' descriptions and decides who to involve next.

## Files

| File | Purpose |
|------|---------|
| `module-06.ipynb` | Step-by-step notebook: create agents → build swarm → run → inspect path |
| `chat.py` | Run the swarm interactively from the terminal |
| `requirements.txt` | `strands-agents>=1.52.0` |

## Agents

| Agent | Role | Routing signal |
|-------|------|----------------|
| `monitor` | Entry point — triages and classifies | Routes to network_specialist or db_admin |
| `network_specialist` | Network/infra root cause analysis | May route to db_admin or resolver |
| `db_admin` | Database root cause analysis | Routes to resolver |
| `resolver` | Synthesizes findings → resolution plan | Final agent |

## Key concepts

- `Swarm([agents], entry_point=agent)`: no routing code, agents decide
- `description` field: the routing signal; write it for the model, not for humans
- `handoff_to_agent`: automatically added to each agent by the SDK
- `result.node_history`: the path that emerged at runtime
- `result.results["agent_name"]`: output from a specific agent

## Strands Agents SDK

```python
from strands import Agent
from strands.multiagent import Swarm

monitor          = Agent(name="monitor",           description="Entry point...", system_prompt="...")
network_specialist = Agent(name="network_specialist", description="Network/infra...", system_prompt="...")
db_admin         = Agent(name="db_admin",          description="Database...", system_prompt="...")
resolver         = Agent(name="resolver",          description="Final resolution...", system_prompt="...")

swarm = Swarm(
    [monitor, network_specialist, db_admin, resolver],
    entry_point=monitor,
    max_handoffs=8,
    max_iterations=12,
)
result = swarm(incident_report)
# result.status, result.node_history, result.results["resolver"]
```

## Prerequisites

- Python 3.10 or higher

## Run

```bash
pip install -r requirements.txt
python chat.py
```

## Next

→ [Module 7: Agent-as-Tool](../07-agent-as-tool/)
