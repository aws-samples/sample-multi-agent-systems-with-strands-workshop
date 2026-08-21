# Module 8: Capstone — Decision-Memo System

**"Brief in, leadership memo out."**  
All four multi-agent patterns combined into one complete pipeline.

**Strands primitives:** `@tool` · `asyncio.gather` · `GraphBuilder` + cycle

## Architecture

![Decision-Memo System: Orchestrator → parallel_heads (Planner, Researcher, Analyzer 1, Analyzer 2) → program_revisor (Program Revisor ↔ Critic) → Leadership Memo](./architecture.png)

## Patterns combined

| Pattern | Component | Strands API |
|---------|-----------|-------------|
| **P5 Agent-as-Tool** | Orchestrator delegates to three specialist tools | `@tool` wrapping `Agent` |
| **P1 Sequential** | Researcher gathers data; passed to analyzers | Python sequence |
| **P2 Fork-Join** | Analyzers A, B, C run simultaneously | `asyncio.gather` + `invoke_async` |
| **P3 Critic-Refiner** | Writer drafts memo → Critic approves or requests revision | `GraphBuilder` + cycle edge |

## Agents

| Agent | Role |
|-------|------|
| **Researcher** | Gathers company data, benchmarks, and competitor intelligence |
| **Analyzer A/B/C** | Evaluates one option each; all three run in parallel |
| **Writer** | Drafts the executive leadership memo |
| **Critic** | Quality gate: APPROVED or REVISION NEEDED |
| **Orchestrator** | Coordinates the three tools; LLM decides call sequence |

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
