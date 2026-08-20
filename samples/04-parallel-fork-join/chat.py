"""Interactive chat for Module 4: Parallel / Fork-Join.

Uses GraphBuilder parallel topology: the Strands-native way to run agents
in parallel. No asyncio needed: the SDK handles execution.

    cd samples/04-parallel-fork-join
    uv pip install -r requirements.txt
    uv run python chat.py

Model options (pass model= to each Agent to switch):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")  # default
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # AWS credits
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-single-agent"))

from strands import Agent
from strands.multiagent import GraphBuilder
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCHER_PROMPT  = "Market research specialist. Use tools to gather data. Return structured findings."
ANALYZER_A_PROMPT  = "Evaluate Option A ($19.99/mo invite-only). Strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. 150 words."
ANALYZER_B_PROMPT  = "Evaluate Option B ($14.99/mo 5% pilot). Strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. 150 words."
ANALYZER_C_PROMPT  = "Evaluate Option C ($12.99/mo full launch). Strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. 150 words."
SYNTHESIZER_PROMPT = "Write a leadership memo: Recommendation, Options table A/B/C, Top 3 Risks, Success Metrics, Decision Required. Under 400 words."


def build_graph():
    researcher  = Agent(name="researcher",  system_prompt=RESEARCHER_PROMPT,
                        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
                        callback_handler=None)
    analyzer_a  = Agent(name="analyzer_a",  system_prompt=ANALYZER_A_PROMPT, callback_handler=None)
    analyzer_b  = Agent(name="analyzer_b",  system_prompt=ANALYZER_B_PROMPT, callback_handler=None)
    analyzer_c  = Agent(name="analyzer_c",  system_prompt=ANALYZER_C_PROMPT, callback_handler=None)
    synthesizer = Agent(name="synthesizer", system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyzer_a,  "analyzer_a")
    builder.add_node(analyzer_b,  "analyzer_b")
    builder.add_node(analyzer_c,  "analyzer_c")
    builder.add_node(synthesizer, "synthesizer")

    builder.add_edge("researcher", "analyzer_a")
    builder.add_edge("researcher", "analyzer_b")
    builder.add_edge("researcher", "analyzer_c")
    builder.add_edge("analyzer_a", "synthesizer")
    builder.add_edge("analyzer_b", "synthesizer")
    builder.add_edge("analyzer_c", "synthesizer")

    builder.set_execution_timeout(300)
    return builder.build()


def main():
    print("Parallel Fork-Join (GraphBuilder) | type 'quit' to exit\n")
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
        graph = build_graph()

        print("\nRunning GraphBuilder parallel Fork-Join...")
        t0 = time.time()
        result = graph(brief)
        elapsed = time.time() - t0

        path = [n.node_id for n in result.execution_order]
        print(f"\nStatus: {result.status} | {elapsed:.1f}s")
        print(f"Execution order: {' → '.join(path)}")
        print()
        for node in reversed(result.execution_order):
            if node.node_id == "synthesizer":
                print("─" * 60)
                print(str(node.result))
                print("─" * 60)
                break
        print()


if __name__ == "__main__":
    main()
