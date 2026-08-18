"""Interactive chat for Module 7: Decision-Memo Capstone.

Runs the full 4-pattern pipeline:
  P1 Sequential: Researcher gathers data
  P2 Fork-Join:  3 analyzers run in parallel
  P3 Critic-Refiner: Writer + Critic quality loop
  P5 Agent-as-Tool: Orchestrator coordinates all three

    cd samples/07-capstone
    pip install -r requirements.txt
    python chat.py

Type 'quit' or Ctrl+C to stop.

Model options (pass model= to each Agent to switch):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")  # default
    model = BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # AWS credits
"""

import sys, os, time, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "01-strands-foundations"))

from strands import Agent, tool
from strands.multiagent import GraphBuilder
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCHER_PROMPT = "You are a market research specialist. Use tools to gather data. Return structured findings."
ANALYZER_PROMPT = "Evaluate ONE option: strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. 100 words max."
WRITER_PROMPT = (
    "Write a leadership memo with: ## Recommendation, ## Options at a Glance (table A/B/C), "
    "## Top 3 Risks+mitigations, ## Success Metrics (numeric targets), ## Decision Required. "
    "If given feedback, revise."
)
CRITIC_PROMPT = (
    "Check: 1)Recommendation. 2)Options table A/B/C. 3)3 Risks+mitigations. "
    "4)2+ Metrics with targets. 5)Decision Required with owner+deadline.\n"
    "Respond: APPROVED or REVISION NEEDED: [criteria numbers]"
)
ORCHESTRATOR_PROMPT = (
    "Coordinate the Decision Intelligence pipeline:\n"
    "1. Call researcher_agent.\n"
    "2. Call parallel_analyzers with brief and research.\n"
    "3. Call critic_refiner with brief and analyses.\n"
    "Execute all three steps."
)


@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitor intelligence.
    Args:
        topic: The decision topic to research
    """
    worker = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT, callback_handler=None)
    return str(worker(topic))


@tool
def parallel_analyzers(brief: str, research_context: str) -> str:
    """Run all three option analyzers (A, B, C) simultaneously and return combined analyses.
    Args:
        brief: The original decision brief
        research_context: Research findings from researcher_agent
    """
    a = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    b = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    c = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)

    async def fork():
        return await asyncio.gather(
            a.invoke_async(f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research_context}"),
            b.invoke_async(f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research_context}"),
            c.invoke_async(f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research_context}"),
        )

    ra, rb, rc = asyncio.run(fork())
    return f"OPTION A:\n{ra}\n\nOPTION B:\n{rb}\n\nOPTION C:\n{rc}"


@tool
def critic_refiner(brief: str, analyses: str) -> str:
    """Draft and quality-check the memo through a critic loop. Returns the approved memo.
    Args:
        brief: The original decision brief
        analyses: Combined analyses from parallel_analyzers
    """
    writer = Agent(name="writer", system_prompt=WRITER_PROMPT, callback_handler=None)
    critic = Agent(name="critic", system_prompt=CRITIC_PROMPT, callback_handler=None)

    def needs_revision(state):
        r = state.results.get("critic")
        return bool(r) and "revision needed" in str(r.result).lower()

    builder = GraphBuilder()
    builder.add_node(writer, "writer")
    builder.add_node(critic, "critic")
    builder.set_entry_point("writer")
    builder.add_edge("writer", "critic")
    builder.add_edge("critic", "writer", condition=needs_revision)
    builder.set_max_node_executions(6)
    builder.set_execution_timeout(120)
    builder.reset_on_revisit(True)

    result = builder.build()(f"Brief:\n{brief}\n\nAnalyses:\n{analyses}")
    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            return str(node.result)
    return str(result)


def main():
    print("Decision-Memo Capstone Pipeline | type 'quit' to exit\n")
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
            tools=[researcher_agent, parallel_analyzers, critic_refiner],
            system_prompt=ORCHESTRATOR_PROMPT,
        )
        print("\nRunning full pipeline (P1→P2→P3 via P5 orchestrator)...")
        t0 = time.time()
        orchestrator(brief)
        elapsed = time.time() - t0

        calls = sum(1 for msg in orchestrator.messages
                    for b in msg.get("content", []) if "toolUse" in b)
        summary = orchestrator.messages  # already streamed
        print(f"\n⏱️  {elapsed:.1f}s | 🔧 {calls} pipeline stages")
        print()


if __name__ == "__main__":
    main()
