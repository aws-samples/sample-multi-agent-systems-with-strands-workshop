# Module 2: Sequential Chain

**Pattern 1 from the deck.** Break the single-agent ceiling with a 3-stage pipeline where each agent has one focused job and passes its output to the next.

## Architecture

```
Decision Brief
      │
      ▼
 ┌────────────┐  callback_handler=None
 │ Researcher │  gathers data with tools
 └─────┬──────┘
       │ str(result)
       ▼
 ┌────────────┐  callback_handler=None
 │  Analyst   │  evaluates all three options
 └─────┬──────┘
       │ str(result)
       ▼
 ┌─────────────┐  streams to participant
 │ Synthesizer │  writes executive memo
 └─────────────┘
```

## What you'll build

A 3-stage pipeline: Researcher → Analyst → Synthesizer. Each agent has a narrow system prompt and a small context window — only what it needs for its role.

## Files

| File | Purpose |
|------|---------|
| `module-02.ipynb` | Step-by-step notebook: prompts → pipeline → inspect → metrics |
| `chat.py` | Run the pipeline interactively from the terminal |
| `requirements.txt` | `strands-agents>=1.52.0` |

## Key concepts

- Sequential pipeline — output of one agent is the input of the next
- `callback_handler=None` — silent intermediate agents; only the final one streams
- Each agent has a **small, focused context** — no single agent holds everything
- `str(result)` — convert `AgentResult` to string for chaining

## Strands API

```python
from strands import Agent

researcher = Agent(system_prompt=RESEARCHER_PROMPT, callback_handler=None)
analyst    = Agent(system_prompt=ANALYST_PROMPT, callback_handler=None)
synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT)

research = researcher(f"Gather data for: {brief}")
analysis = analyst(f"Brief: {brief}\n\nResearch: {research}")
memo     = synthesizer(f"Brief: {brief}\n\nResearch: {research}\n\nAnalysis: {analysis}")
```

## Run

```bash
pip install -r requirements.txt
python chat.py
```

## Prerequisites

Module 1 — this module imports tools from `../01-strands-foundations/decision_brief_tools.py`.

## Next

→ [Module 3: Parallel Fork-Join](../03-parallel-fork-join/)
