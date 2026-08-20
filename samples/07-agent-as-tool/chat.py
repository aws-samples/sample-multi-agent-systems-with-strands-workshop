"""Interactive chat for Module 7: Agent as a Tool.

Orchestrator delegates to 4 specialists wrapped as @tool:
  Research Agent, Finance Agent, Legal Agent, Writer Agent.

    cd samples/07-agent-as-tool
    pip install -r requirements.txt
    python chat.py

Type 'quit' or Ctrl+C to stop.
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-single-agent"))

from strands import Agent, tool
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCH_PROMPT = (
    "You are a market research specialist. Use your tools to gather company data, "
    "industry benchmarks, and competitive intelligence. Return structured findings: data only."
)
FINANCE_PROMPT = (
    "You are a financial analyst. Return: revenue projections, unit economics, "
    "ROI estimate, capital efficiency, and an investment verdict (Invest / Pass). "
    "Be specific with numbers. 200 words max."
)
WRITER_PROMPT = (
    "Write a professional investment memo:\n"
    "## Executive Summary\n## Market Opportunity\n## Financial Highlights\n"
    "## Risk Assessment\n## Recommendation\nUnder 450 words."
)
LEGAL_PROMPT = (
    "Review the investment brief for regulatory risks, data privacy (GDPR/CCPA), "
    "contractual obligations, IP, and due diligence flags. "
    "Return bullet-point legal risks with severity (High/Medium/Low). 150 words max."
)
ORCHESTRATOR_PROMPT = (
    "You are an investment committee coordinator. For each investment request:\n"
    "1. Call research_agent to gather company and market data.\n"
    "2. Call finance_agent with the brief and research findings.\n"
    "3. Call legal_agent with the brief to identify legal risks.\n"
    "4. Call writer_agent with all findings to produce the final memo.\n"
    "Execute all four steps."
)


@tool
def research_agent(topic: str) -> str:
    """Gather market data, company metrics, and competitive intelligence for an investment topic.

    Args:
        topic: The company or investment topic to research
    """
    worker = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCH_PROMPT,
        callback_handler=None,
    )
    return str(worker(topic))


@tool
def finance_agent(brief: str, research_context: str) -> str:
    """Analyze financial viability: ROI, unit economics, projections, and investment verdict.

    Args:
        brief: The original investment brief
        research_context: Market and company data from research_agent
    """
    worker = Agent(system_prompt=FINANCE_PROMPT, callback_handler=None)
    return str(worker(f"Brief:\n{brief}\n\nResearch:\n{research_context}"))


@tool
def legal_agent(brief: str) -> str:
    """Review legal and compliance risks: regulatory exposure, data privacy, IP, due diligence flags.

    Args:
        brief: The investment brief to review
    """
    worker = Agent(system_prompt=LEGAL_PROMPT, callback_handler=None)
    return str(worker(brief))


@tool
def writer_agent(brief: str, research_context: str, financial_analysis: str, legal_review: str) -> str:
    """Write the final investment memo. Call LAST — after all other specialists.

    Args:
        brief: The original investment brief
        research_context: Findings from research_agent
        financial_analysis: Analysis from finance_agent
        legal_review: Risk review from legal_agent
    """
    worker = Agent(system_prompt=WRITER_PROMPT)
    return str(worker(
        f"Brief:\n{brief}\n\nResearch:\n{research_context}\n\n"
        f"Financial:\n{financial_analysis}\n\nLegal:\n{legal_review}"
    ))


def main():
    print("Agent-as-Tool — Investment Analysis | type 'quit' to exit\n")
    DEFAULT_BRIEF = """
INVESTMENT BRIEF: NovaCart — Premium Subscription Tier

Company: NovaCart (e-commerce, 2M active users)
Proposal: Premium subscription tier — $2M investment ask
Options: A (Invite-only $19.99/mo) | B (5% pilot $14.99/mo) | C (Full launch $12.99/mo)
Target return: +15% CLV in 6 months
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
            tools=[research_agent, finance_agent, legal_agent, writer_agent],
            system_prompt=ORCHESTRATOR_PROMPT,
        )
        print("\nOrchestrator running (LLM delegates to 4 specialists)...")
        t0 = time.time()
        orchestrator(brief)
        elapsed = time.time() - t0

        tool_calls = sum(
            1 for msg in orchestrator.messages
            for block in msg.get("content", [])
            if "toolUse" in block
        )
        print(f"\n{elapsed:.1f}s | {tool_calls} tool calls (research + finance + legal + writer)")
        print()


if __name__ == "__main__":
    main()
