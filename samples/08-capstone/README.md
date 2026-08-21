# Module 8: Capstone — Decision-Memo System

**"Brief in, leadership memo out."**  
All four multi-agent patterns combined into one complete pipeline.

**Strands primitives:** `@tool` · `asyncio.gather` · `GraphBuilder` + cycle

## Architecture

![Decision-Memo System: Orchestrator → parallel_heads (Planner, Researcher, Analyzer 1, Analyzer 2) → program_revisor (Program Revisor ↔ Critic) → Leadership Memo](./architecture.png)

## Patterns combined

| Pattern | Component | Strands API |
|---------|-----------|-------------|
| **P2 Parallel heads** | Planner + Researcher + Analyzer 1 + Analyzer 2 run simultaneously | `asyncio.gather` + `invoke_async` |
| **P3 Critic-Refiner** | Program Revisor drafts → Critic evaluates → loop until APPROVED | `GraphBuilder` + cycle edge |
| **P5 Agent-as-Tool** | Orchestrator delegates to both tools | `@tool` wrapping sub-pipelines |
| **P1 Sequential** | Parallel phase completes → Program Revisor synthesizes | Implicit sequencing |

## Agents

| Agent | Role |
|-------|------|
| **Planner** | Creates the analysis plan from the brief |
| **Researcher** | Gathers market data with business intelligence tools |
| **Analyzer 1** | Financial analysis of all 3 options (ROI, payback, budget) |
| **Analyzer 2** | Risk analysis of all 3 options (complexity, mitigations) |
| **Program Revisor** | Synthesizes all findings into the leadership memo |
| **Critic** | Quality gate: checks 5 criteria; APPROVED or REVISION NEEDED |

## Files

| File | Purpose |
|------|---------|
| `module-08.ipynb` | Step-by-step notebook: build tools → orchestrator → run → inspect |
| `chat.py` | Run the complete pipeline interactively from the terminal |
| `requirements.txt` | `strands-agents>=1.52.0`, `nest-asyncio>=1.6.0` |
| `production/` | Deploy to Amazon Bedrock AgentCore Runtime |

## Run

```bash
uv pip install -r requirements.txt
uv run python chat.py
```

## What happens at runtime

1. Orchestrator calls `parallel_heads(brief)` — Planner, Researcher, Analyzer 1, Analyzer 2 run simultaneously via `asyncio.gather`
2. Orchestrator calls `program_revisor(brief, parallel_findings)` — Program Revisor drafts, Critic evaluates, loop until `APPROVED`
3. Final approved memo returned

Typical execution: ~120s, ~15K tokens (Claude Sonnet 4 on Amazon Bedrock).

## Deploy to production

```bash
cd production/
cat README.md
```

## Prerequisites

- Python 3.10 or higher
- Modules 01–07. This module reuses tools from `../02-single-agent/decision_brief_tools.py`.
