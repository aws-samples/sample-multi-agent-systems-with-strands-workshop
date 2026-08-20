"""Interactive chat for Module 3: Sequential Chain.

Uses Strands GraphBuilder (Workflow / DAG) to run the 3-stage pipeline:
  Researcher → Analyst → Synthesizer

Each node's output becomes the next node's input — the chain.
The GraphBuilder is the Strands primitive for deterministic sequential workflows.

    cd samples/03-sequential-chain
    uv pip install -r requirements.txt
    uv run python chat.py

Type 'quit' or Ctrl+C to stop.

Model options (pass model= to each Agent to switch):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")  # default
    model = BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # AWS credits
    model = BedrockModel(model_id="amazon.nova-lite-v1:0")  # cheapest
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-single-agent"))

from strands import Agent
from strands.multiagent import GraphBuilder
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCHER_PROMPT = '''You are a market research specialist.
Given a decision brief, gather relevant company data, market benchmarks, and competitor intelligence.
Use your tools. Return structured findings: data only, no recommendations.'''

ANALYST_PROMPT = '''You are a business strategy analyst.
Given market research findings and a decision brief, analyze each option (A, B, C).
For each option produce: strengths, weaknesses, implementation complexity (Low/Med/High),
top 2 risks with mitigations, and a verdict (Proceed / Proceed with caution / Do not proceed).
Return structured analysis only: no executive memo yet.'''

SYNTHESIZER_PROMPT = '''You are an executive communications specialist.
Given research findings, option analyses, and the original brief, write a leadership memo:

## Decision Memo: [Title]
**Recommendation**: [one sentence: which option and why]

### Options at a Glance
| | Option A | Option B | Option C |
|---|---|---|---|
| Complexity | | | |
| Risk level | | | |
| Verdict | | | |

### Top 3 Risks & Mitigations
### Success Metrics (3-5 KPIs)
### Decision Required: owner, deadline, approvers

Under 400 words. Be direct.'''


def run_chain(brief: str) -> str:
    """Run the sequential chain via Strands GraphBuilder."""
    researcher = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT,
        callback_handler=None,
    )
    analyst     = Agent(system_prompt=ANALYST_PROMPT,     callback_handler=None)
    synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyst,     "analyst")
    builder.add_node(synthesizer, "synthesizer")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst",    "synthesizer")
    builder.set_execution_timeout(300)

    result = builder.build()(brief)

    for node in reversed(result.execution_order):
        if node.node_id == "synthesizer":
            return str(node.result).strip()
    return str(result).strip()


def main():
    print("Sequential Chain — Strands GraphBuilder (Workflow / DAG)")
    print("Submit a decision brief. Type 'quit' to exit.\n")
    print("Default brief: NovaCart Premium Tier. Press Enter to use it.\n")

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
        print(run_chain(brief))
        print("\n" + "─" * 60 + "\n")


if __name__ == "__main__":
    main()
