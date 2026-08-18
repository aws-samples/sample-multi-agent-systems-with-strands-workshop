"""Interactive chat for Module 4: Critic-Refiner.

Runs the GraphBuilder feedback loop: Writer → Critic → [APPROVED | REVISION NEEDED → Writer → ...]

    cd samples/04-critic-refiner
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

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-single-agent"))

from strands import Agent
from strands.multiagent import GraphBuilder
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCHER_PROMPT = '''You are a market research specialist.
Gather company data, benchmarks, and competitor intelligence using your tools.
Return structured findings: data only.'''

WRITER_PROMPT = (
    "You are an executive memo writer. Write a COMPLETE leadership memo with exactly these 5 labeled sections:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table comparing A, B, C on Complexity/Risk/Verdict)\n"
    "## Top 3 Risks (each risk with a specific mitigation action)\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, who must approve)\n"
    "If you receive feedback, revise and include ALL 5 sections in the new version."
)

CRITIC_PROMPT = (
    "You are a quality critic. Check ONLY these 5 criteria:\n"
    "1. '## Recommendation' section with a clear option choice (A, B, or C)\n"
    "2. '## Options at a Glance' table comparing A, B, C\n"
    "3. '## Top 3 Risks' with at least 3 risks each with a specific mitigation\n"
    "4. '## Success Metrics' with at least 2 KPIs that have numeric targets\n"
    "5. '## Decision Required' with both owner AND deadline\n"
    "DO NOT check for research data, background context, or any section not listed.\n"
    "Respond with EXACTLY one of:\n"
    "APPROVED\n"
    "(if all 5 criteria are met)\n"
    "REVISION NEEDED: [which criterion numbers are missing or incomplete]\n"
    "Your response must start with APPROVED or REVISION NEEDED."
)


def build_graph():
    writer = Agent(system_prompt=WRITER_PROMPT, callback_handler=None)
    critic = Agent(system_prompt=CRITIC_PROMPT, callback_handler=None)

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
    return builder.build()


def run_critic_refiner(brief: str) -> None:
    """Run the full pipeline: Research → GraphBuilder critic loop."""
    researcher = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT,
        callback_handler=None,
    )
    print("\nStep 1/2: Researcher gathering context...")
    research = str(researcher(f"Gather data for this decision:\n{brief}"))
    print(f"  Done: {len(research)} chars")

    print("\nStep 2/2: Critic-Refiner loop:")
    graph = build_graph()
    t0 = time.time()
    result = graph(f"{brief}\n\nResearch:\n{research}")

    print(f"\nStatus: {result.status} | {time.time()-t0:.1f}s")
    cycles = len(result.execution_order)
    writer_runs = sum(1 for n in result.execution_order if n.node_id == "writer")
    critic_runs = sum(1 for n in result.execution_order if n.node_id == "critic")
    print(f"Cycles: {cycles} nodes ({writer_runs} drafts, {critic_runs} reviews)")

    for node in result.execution_order:
        if node.node_id == "critic":
            print(f"  Critic: {str(node.result)[:80].strip()}")

    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            print(f"\nFinal memo:\n{'─'*60}")
            print(str(node.result))
            print("─" * 60)
            break


def main():
    print("Critic-Refiner Pipeline | type 'quit' to exit\n")
    DEFAULT_BRIEF = """
DECISION BRIEF: NovaCart Premium Tier Launch
Options: A (Exclusive $19.99/mo) | B (5% pilot $14.99/mo) | C (Full launch $12.99/mo)
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
        run_critic_refiner(user_input if user_input else DEFAULT_BRIEF)
        print()


if __name__ == "__main__":
    main()
