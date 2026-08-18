"""Interactive chat for Module 5: Dynamic Swarm.

Runs the 3-agent swarm (Researcher → Analyst → Writer) where agents
hand off autonomously — no fixed routing.

    cd samples/05-dynamic-swarm
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-strands-foundations"))

from strands import Agent
from strands.multiagent import Swarm
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data


def build_swarm():
    researcher = Agent(
        name="researcher",
        description=(
            "Market research specialist with tools to retrieve company financial data, "
            "industry benchmarks, and competitor premium tier intelligence. "
            "Use me first when you need data to inform the analysis."
        ),
        system_prompt=(
            "You are a market research specialist. Use your tools to gather relevant data. "
            "Summarize findings and hand off to the analyst."
        ),
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        callback_handler=None,
    )
    analyst = Agent(
        name="analyst",
        description=(
            "Business strategy analyst who evaluates options A/B/C. "
            "Use me after research is complete."
        ),
        system_prompt=(
            "You are a business strategy analyst. Evaluate each option (A, B, C): "
            "strengths, weaknesses, complexity, top 2 risks+mitigations, verdict. "
            "Hand off to the writer when done."
        ),
        callback_handler=None,
    )
    writer = Agent(
        name="writer",
        description="Executive memo writer. Use me last to produce the final leadership decision memo.",
        system_prompt=(
            "You are an executive memo writer. Write the final memo: "
            "Recommendation, Options table, Top 3 Risks+mitigations, Success Metrics, Decision Required. "
            "Do NOT hand off."
        ),
        callback_handler=None,
    )
    return Swarm(
        [researcher, analyst, writer],
        entry_point=researcher,
        max_handoffs=6,
        max_iterations=10,
        execution_timeout=180.0,
        node_timeout=60.0,
    )


def main():
    print("Dynamic Swarm Pipeline | type 'quit' to exit\n")
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

        brief = user_input if user_input else DEFAULT_BRIEF
        swarm = build_swarm()
        print("\nRunning (agents decide the path autonomously)...")
        t0 = time.time()
        result = swarm(brief)
        elapsed = time.time() - t0

        path = [n.node_id for n in result.node_history]
        usage = result.accumulated_usage
        print(f"\nStatus: {result.status} | {elapsed:.1f}s")
        print(f"Path emerged: {' → '.join(path)}")
        print(f"Tokens: {usage.get('totalTokens', 0):,}")
        print()
        print("─" * 60)
        print(str(result.results.get("writer", "No writer output")))
        print("─" * 60)
        print()


if __name__ == "__main__":
    main()
