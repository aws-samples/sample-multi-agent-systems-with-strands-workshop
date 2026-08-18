"""Interactive chat for Module 3: Parallel / Fork-Join.

Runs the full pipeline: Researcher → [A ∥ B ∥ C] → Synthesizer.
Each run forks three analyzers in parallel, then merges results.

    cd samples/03-parallel-fork-join
    pip install -r requirements.txt
    python chat.py

Type 'quit' or Ctrl+C to stop.

Model options (pass model= to each Agent to switch):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")  # default
    model = BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # AWS credits
    model = BedrockModel(model_id="amazon.nova-lite-v1:0")  # cheapest
"""

import sys, os, asyncio, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-strands-foundations"))

from strands import Agent
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCHER_PROMPT = '''You are a market research specialist.
Gather company data, benchmarks, and competitor intelligence using your tools.
Return structured findings — data only, no recommendations.'''

ANALYZER_PROMPT = '''You are a business strategy analyst focused on ONE option.
Evaluate the option assigned to you: strengths, weaknesses, complexity (Low/Med/High),
top 2 risks with mitigations, verdict (Proceed / Proceed with caution / Do not proceed).
Be concise — 150 words max.'''

SYNTHESIZER_PROMPT = '''You are an executive communications specialist.
Given research findings and analyses of three options, write a leadership memo:

## Decision Memo
**Recommendation**: [one sentence — which option and why]

### Options at a Glance
| | Option A | Option B | Option C |
|---|---|---|---|
| Complexity | | | |
| Risk level | | | |
| Verdict | | | |

### Top 3 Risks & Mitigations
### Success Metrics (3-5 KPIs)
### Decision Required: owner · deadline · approvers

Under 400 words.'''


async def run_pipeline(brief: str) -> None:
    """Full Fork-Join pipeline: Research → [A∥B∥C] → Synthesize."""

    # ── Step 1: Research (sequential) ────────────────────────────────────
    print("\nStep 1/3 — Researcher gathering data...")
    researcher = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT,
        callback_handler=None,
    )
    t0 = time.time()
    research = researcher(f"Gather market data for this decision:\n{brief}")
    research_text = str(research)
    print(f"  Done in {time.time()-t0:.1f}s")

    # ── Step 2: Fork — 3 analyzers in parallel ────────────────────────────
    print("\nStep 2/3 — Forking 3 analyzers in parallel...")
    analyzer_a = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    analyzer_b = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    analyzer_c = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)

    t1 = time.time()
    result_a, result_b, result_c = await asyncio.gather(
        analyzer_a.invoke_async(
            f"Option A (Exclusive Premium $19.99/mo, invite-only top 10% spenders)\n"
            f"Brief: {brief}\nResearch: {research_text}"
        ),
        analyzer_b.invoke_async(
            f"Option B (Gradual Rollout $14.99/mo, 5% A/B pilot with kill-switch)\n"
            f"Brief: {brief}\nResearch: {research_text}"
        ),
        analyzer_c.invoke_async(
            f"Option C (Full Launch $12.99/mo, open to all users, 30-day trial)\n"
            f"Brief: {brief}\nResearch: {research_text}"
        ),
    )
    print(f"  Join complete in {time.time()-t1:.1f}s (all 3 ran simultaneously)")

    # ── Step 3: Synthesize (sequential) ──────────────────────────────────
    print("\nStep 3/3 — Synthesizing executive memo:\n" + "─" * 60)
    synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT)
    synthesizer(
        f"Brief:\n{brief}\n\nResearch:\n{research_text}\n\n"
        f"Option A analysis:\n{result_a}\n\n"
        f"Option B analysis:\n{result_b}\n\n"
        f"Option C analysis:\n{result_c}"
    )
    print("─" * 60)


def main():
    print("Parallel Fork-Join Pipeline | type 'quit' to exit\n")

    DEFAULT_BRIEF = """
DECISION BRIEF: NovaCart Premium Tier Launch
Options: A (Exclusive $19.99) | B (5% pilot $14.99) | C (Full launch $12.99)
Success target: +15% CLV in 6 months | Budget: $2M | Deadline: 2027-01-31
"""

    while True:
        try:
            user_input = input("Brief (Enter for default): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        brief = user_input if user_input else DEFAULT_BRIEF
        asyncio.run(run_pipeline(brief))
        print()


if __name__ == "__main__":
    main()
