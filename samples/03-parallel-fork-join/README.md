# Module 3: Parallel Fork-Join

**Pattern 2 from the deck.** Fork independent sub-tasks to run simultaneously, then merge results — latency drops to the slowest single worker.

## Architecture

```
Decision Brief
      │
      ▼
 ┌────────────┐  (sequential)
 │ Researcher │  gathers shared context
 └──────┬─────┘
        │ research_text (shared)
   ┌────┴────┬────────┐
   ▼         ▼        ▼    asyncio.gather → all 3 run at once
 Analyzer A  B        C
   └────┬────┴────────┘
        │ join: wait for all 3
        ▼
 ┌─────────────┐  (sequential)
 │ Synthesizer │  merges all analyses
 └─────────────┘
```

## What you'll build

A pipeline that forks three Option Analyzers (A, B, C) in parallel using `asyncio.gather` and `invoke_async`, then merges their analyses into a final memo.

## Files

| File | Purpose |
|------|---------|
| `module-03.ipynb` | Step-by-step notebook: setup → research → fork → join → synthesize → metrics |
| `chat.py` | Run the parallel pipeline interactively |
| `requirements.txt` | `strands-agents>=1.52.0`, `nest-asyncio>=1.6.0` |

## Key concepts

- `agent.invoke_async(prompt)` — runs an agent as a coroutine (non-blocking)
- `asyncio.gather(...)` — fork: starts N coroutines simultaneously; join: waits for all
- `nest_asyncio.apply()` — required for `asyncio.gather` inside Jupyter notebooks
- Wall-clock time ≈ slowest single analyzer (not sum of all three)

## Strands API

```python
import asyncio
import nest_asyncio
nest_asyncio.apply()

from strands import Agent

analyzer_a = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
analyzer_b = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
analyzer_c = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)

result_a, result_b, result_c = asyncio.run(asyncio.gather(
    analyzer_a.invoke_async(f"Option A...\nResearch: {research_text}"),
    analyzer_b.invoke_async(f"Option B...\nResearch: {research_text}"),
    analyzer_c.invoke_async(f"Option C...\nResearch: {research_text}"),
))
```

## Run

```bash
pip install -r requirements.txt
python chat.py
```

## Prerequisites

Module 1 — imports tools from `../01-strands-foundations/decision_brief_tools.py`.

## Next

→ [Module 4: Critic-Refiner](../04-critic-refiner/)
