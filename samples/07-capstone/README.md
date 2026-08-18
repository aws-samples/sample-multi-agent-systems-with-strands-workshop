# Module 7: Capstone — Decision-Memo System

Combine all four multi-agent patterns into one complete Decision Intelligence pipeline — from a decision brief to an approved leadership memo.

## Architecture

![Decision-Memo Capstone on AgentCore: Client → Orchestrator Runtime → Researcher, Analyzers (parallel), Critic-Refiner → Amazon Bedrock + CloudWatch](./architecture.png)


## Patterns combined

| Pattern | Component | Strands Agents SDK |
|---------|-----------|-------------|
| P1 Sequential | Research phase | Python sequence |
| P2 Fork-Join | Three parallel analyzers | `asyncio.gather` + `invoke_async` |
| P3 Critic-Refiner | Memo quality gate | `GraphBuilder` + cycle edge |
| P5 Agent-as-Tool | Orchestrator delegates all three | `@tool` wrapping each sub-pipeline |

## Files

| File | Purpose |
|------|---------|
| `module-07.ipynb` | Full capstone notebook: prompts → tools → orchestrator → inspect → metrics |
| `chat.py` | Run the complete pipeline interactively |
| `requirements.txt` | `strands-agents>=1.52.0`, `nest-asyncio>=1.6.0` |

## Run

```bash
pip install -r requirements.txt
python chat.py
```

## Prerequisites

All previous modules. Imports tools from `../01-strands-foundations/decision_brief_tools.py`.

## What happens at runtime

1. Orchestrator calls `researcher_agent(topic)` → uses 3 business intel tools
2. Orchestrator calls `parallel_analyzers(brief, research)` → forks A/B/C analyzers with `asyncio.gather`
3. Orchestrator calls `critic_refiner(brief, analyses)` → `GraphBuilder` writer-critic loop until `APPROVED`
4. Final approved memo returned to the orchestrator's context

Typical execution: ~50s, ~11K tokens total.

## Next

→ [Module 8: Deploy to AgentCore](../08-deploy-agentcore/)
