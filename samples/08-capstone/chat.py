"""Interactive chat for Module 8: Decision-Memo System (Capstone).

All 4 patterns combined:
  P2 Parallel heads  — Planner + Researcher + Analyzer 1 + Analyzer 2 run simultaneously
  P3 Critic-Refiner  — Program Revisor ↔ Critic quality loop
  P5 Agent-as-Tool   — Orchestrator delegates via @tool
  P1 Sequential      — Parallel phase → Program Revisor synthesis

    cd samples/08-capstone
    pip install -r requirements.txt
    python chat.py

Type 'quit' or Ctrl+C to stop.
"""

import sys, os, asyncio, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-single-agent"))

import nest_asyncio
nest_asyncio.apply()

from strands import Agent, tool
from strands.multiagent import GraphBuilder
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

PLANNER_PROMPT = (
    "You are a decision planner. Analyze the brief: identify key questions, "
    "data needed, and criteria for choosing between options. 80 words max."
)
RESEARCHER_PROMPT = (
    "You are a market research specialist. Use tools to gather data. "
    "Return structured findings: data only."
)
FINANCIAL_ANALYZER_PROMPT = (
    "You are a financial analyst. For ALL three options (A, B, C), analyze: "
    "revenue projections, ROI, payback period, budget fit, financial verdict. 150 words max."
)
RISK_ANALYZER_PROMPT = (
    "You are a risk analyst. For ALL three options (A, B, C), analyze: "
    "implementation complexity (Low/Med/High), top 2 risks per option, mitigations, verdict. 150 words max."
)
PROGRAM_REVISOR_PROMPT = (
    "You are the Program Revisor. Synthesize plan + research + financial + risk into a memo:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table A/B/C: Complexity, Risk, Financial, Verdict)\n"
    "## Top 3 Risks with specific mitigations\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, who approves)\n"
    "Revise if given feedback. Under 400 words."
)
CRITIC_GATE_PROMPT = (
    "Quality critic. Check: 1)Recommendation. 2)Options table A/B/C. "
    "3)3 Risks+mitigations. 4)2+ Metrics with targets. 5)Decision Required owner+deadline.\n"
    "Respond: APPROVED or REVISION NEEDED: [criteria numbers]"
)
ORCHESTRATOR_PROMPT = (
    "Decision-Memo System: "
    "1. Call parallel_heads with the brief — runs 4 specialists simultaneously. "
    "2. Call program_revisor with brief and parallel_findings — Program Revisor↔Critic loop. "
    "Execute both steps in order."
)


@tool
def parallel_heads(brief: str) -> str:
    """Run 4 specialists simultaneously: Planner, Researcher, Analyzer 1 (financial), Analyzer 2 (risk).

    Args:
        brief: The full decision brief
    """
    planner    = Agent(system_prompt=PLANNER_PROMPT,            callback_handler=None)
    researcher = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT, callback_handler=None,
    )
    analyzer_1 = Agent(system_prompt=FINANCIAL_ANALYZER_PROMPT, callback_handler=None)
    analyzer_2 = Agent(system_prompt=RISK_ANALYZER_PROMPT,      callback_handler=None)

    async def fork():
        return await asyncio.gather(
            planner.invoke_async(brief),
            researcher.invoke_async(brief),
            analyzer_1.invoke_async(brief),
            analyzer_2.invoke_async(brief),
        )

    plan_out, research_out, fin_out, risk_out = asyncio.run(fork())
    return (
        f"PLAN:\n{plan_out}\n\n"
        f"RESEARCH:\n{research_out}\n\n"
        f"FINANCIAL ANALYSIS:\n{fin_out}\n\n"
        f"RISK ANALYSIS:\n{risk_out}"
    )


@tool
def program_revisor(brief: str, parallel_findings: str) -> str:
    """Synthesize parallel findings into an approved memo via Program Revisor ↔ Critic loop.

    Args:
        brief: The original decision brief
        parallel_findings: Combined output from parallel_heads
    """
    revisor = Agent(name="program_revisor", system_prompt=PROGRAM_REVISOR_PROMPT, callback_handler=None)
    critic  = Agent(name="critic",          system_prompt=CRITIC_GATE_PROMPT,     callback_handler=None)

    def needs_revision(state):
        r = state.results.get("critic")
        return bool(r) and "revision needed" in str(r.result).lower()

    builder = GraphBuilder()
    builder.add_node(revisor, "program_revisor")
    builder.add_node(critic,  "critic")
    builder.set_entry_point("program_revisor")
    builder.add_edge("program_revisor", "critic")
    builder.add_edge("critic", "program_revisor", condition=needs_revision)
    builder.set_max_node_executions(6)
    builder.set_execution_timeout(180)
    builder.reset_on_revisit(True)

    result = builder.build()(
        f"Brief:\n{brief}\n\nParallel findings:\n{parallel_findings}"
    )
    for node in reversed(result.execution_order):
        if node.node_id == "program_revisor":
            return str(node.result)
    return str(result)


def main():
    print("Decision-Memo System | type 'quit' to exit\n")
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
        orchestrator = Agent(
            tools=[parallel_heads, program_revisor],
            system_prompt=ORCHESTRATOR_PROMPT,
        )
        print("\nRunning: 4 parallel heads → Program Revisor↔Critic loop...")
        t0 = time.time()
        orchestrator(brief)
        elapsed = time.time() - t0

        calls = sum(1 for msg in orchestrator.messages
                    for b in msg.get("content", []) if "toolUse" in b)
        print(f"\n{elapsed:.1f}s | {calls} pipeline stages")
        print()


if __name__ == "__main__":
    main()
