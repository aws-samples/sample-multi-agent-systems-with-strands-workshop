"""Interactive chat for Module 5: Critic-Refiner.

Uses Strands GraphBuilder with a cycle edge:
  Writer drafts → Critic evaluates → REVISION NEEDED loops back → APPROVED exits

    cd samples/05-critic-refiner
    uv pip install -r requirements.txt
    uv run python chat.py

Type 'quit' or Ctrl+C to stop.
"""

from strands import Agent
from strands.multiagent import GraphBuilder

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


def run_critic_refiner(brief: str) -> None:
    """Run the Critic-Refiner GraphBuilder loop on a decision brief."""
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

    result = builder.build()(brief)

    writer_runs = sum(1 for n in result.execution_order if n.node_id == "writer")
    critic_runs = sum(1 for n in result.execution_order if n.node_id == "critic")
    print(f"\nStatus: {result.status} | {writer_runs} drafts, {critic_runs} reviews")

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
    print("Critic-Refiner — Strands GraphBuilder cycle")
    print("Submit a decision brief. Type 'quit' to exit.\n")

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
