"""Interactive chat for Module 8: Decision-Memo System (Capstone).

Combines all four multi-agent patterns:
  P2 Parallel heads: Planner + Researcher + Analyzers run simultaneously
  P3 Critic-Refiner: Program Revisor ↔ Critic quality loop
  P5 Agent-as-Tool:  Orchestrator delegates to both tools
  P1 Sequential:     Program Revisor synthesizes after parallel heads

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
    "You are a decision planner. Analyze the brief and produce a structured analysis plan: "
    "key questions to answer, what data is needed, what criteria matter for choosing between options. "
    "100 words max."
)
RESEARCHER_PROMPT = (
    "You are a market research specialist. Use tools to gather data. "
    "Return structured findings: data only, no recommendations."
)
ANALYZER_PROMPT = (
    "Evaluate ONE option: strengths, weaknesses, complexity (Low/Med/High), "
    "top 2 risks with mitigations, verdict. 100 words max."
)
PROGRAM_REVISOR_PROMPT = (
    "You are an executive memo writer. Synthesize plan and analyses into a COMPLETE leadership memo:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table comparing A, B, C)\n"
    "## Top 3 Risks with specific mitigations\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, who approves)\n"
    "Revise if given feedback. Under 400 words."
)
CRITIC_PROMPT = (
    "Check: 1)Recommendation. 2)Options table A/B/C. 3)3 Risks+mitigations. "
    "4)2+ Metrics with targets. 5)Decision Required with owner+deadline.\n"
    "Respond: APPROVED or REVISION NEEDED: [criteria numbers]"
)
ORCHESTRATOR_PROMPT = (
    "Decision-Memo System: "
    "1. Call parallel_heads with the brief. "
    "2. Call program_revisor with the brief and parallel_findings. "
    "Execute both steps in order."
)


@tool
def parallel_heads(brief: str) -> str:
    """Run Planner, Researcher, Analyzer A, Analyzer B, Analyzer C simultaneously on the brief.

    Args:
        brief: The full decision brief
    """
    planner    = Agent(system_prompt=PLANNER_PROMPT, callback_handler=None)
    researcher = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT, callback_handler=None,
    )
    analyzer_a = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    analyzer_b = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    analyzer_c = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)

    async def fork():
        return await asyncio.gather(
            planner.invoke_async(brief),
            researcher.invoke_async(brief),
            analyzer_a.invoke_async(f"Option A: Exclusive Premium ($19.99/mo, invite-only top 10%)\nBrief: {brief}"),
            analyzer_b.invoke_async(f"Option B: Gradual Rollout ($14.99/mo, 5% A/B pilot)\nBrief: {brief}"),
            analyzer_c.invoke_async(f"Option C: Full Launch ($12.99/mo, open to all, 30-day trial)\nBrief: {brief}"),
        )

    plan_out, research_out, a_out, b_out, c_out = asyncio.run(fork())
    return (
        f"PLAN:\n{plan_out}\n\n"
        f"RESEARCH:\n{research_out}\n\n"
        f"OPTION A:\n{a_out}\n\n"
        f"OPTION B:\n{b_out}\n\n"
        f"OPTION C:\n{c_out}"
    )


@tool
def program_revisor(brief: str, parallel_findings: str) -> str:
    """Synthesize parallel findings into an approved leadership memo via Program Revisor ↔ Critic loop.

    Args:
        brief: The original decision brief
        parallel_findings: Combined output from parallel_heads
    """
    revisor = Agent(name="program_revisor", system_prompt=PROGRAM_REVISOR_PROMPT, callback_handler=None)
    critic  = Agent(name="critic",          system_prompt=CRITIC_PROMPT,          callback_handler=None)

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
        print("\nRunning Decision-Memo System (P2 → P3 via P5)...")
        t0 = time.time()
        orchestrator(brief)
        elapsed = time.time() - t0

        calls = sum(1 for msg in orchestrator.messages
                    for b in msg.get("content", []) if "toolUse" in b)
        print(f"\n{elapsed:.1f}s | {calls} pipeline stages")
        print()


if __name__ == "__main__":
    main()
