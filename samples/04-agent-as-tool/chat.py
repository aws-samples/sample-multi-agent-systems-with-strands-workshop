"""Interactive chat for Module 4: Agent as a Tool.

Same orchestrator as the notebook: it delegates to 4 specialists used as tools.
Research, Finance and Legal are @tool functions that call an Agent; the Writer is
Agent.as_tool(delegate=True), so its memo is returned to you as-is.

    cd samples/04-agent-as-tool
    pip install -r requirements.txt
    python chat.py

Type or paste an investment brief and press Enter, then ask follow-ups. A
multi-line brief pasted at once (like DECISION_BRIEF in samples/shared/decision_brief.py)
is sent as ONE message. Type 'quit' or Ctrl+C to stop.
"""

import json
import os
import select
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-single-agent"))

from strands import Agent, tool
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data


RESEARCH_PROMPT = (
    "You are a market research specialist. Use your tools to gather company data, "
    "industry benchmarks, and competitive intelligence. Return structured findings: data only."
)

FINANCE_PROMPT = (
    "You are a financial analyst. Analyze the investment brief and market data provided. "
    "Return: revenue projections, unit economics (CAC, LTV, payback period), "
    "ROI estimate, capital efficiency, and a financial verdict (Invest / Invest with conditions / Pass). "
    "Be specific with numbers. 200 words max."
)

LEGAL_PROMPT = (
    "You are a legal and compliance reviewer. Review the investment brief for: "
    "regulatory risks, data privacy concerns (GDPR, CCPA), contractual obligations, "
    "IP considerations, and any red flags for due diligence. "
    "Return a bullet-point list of legal risks with severity (High/Medium/Low). 150 words max."
)

WRITER_PROMPT = (
    "You are an investment memo writer. You receive the brief, research findings, financial "
    "analysis, and legal review. Produce a professional investment analysis memo:\n"
    "## Executive Summary (recommendation in one sentence)\n"
    "## Market Opportunity (size, growth, competitive position)\n"
    "## Financial Highlights (key metrics, ROI, projections)\n"
    "## Risk Assessment (top 3 risks with mitigations)\n"
    "## Recommendation (Invest / Invest with conditions / Pass, terms, conditions)\n"
    "Under 450 words. Be direct."
)

ORCHESTRATOR_PROMPT = (
    "You are an investment committee coordinator. For each investment request:\n"
    "1. Call research_agent to gather company and market data.\n"
    "2. Call finance_agent with the brief and research findings to get financial analysis.\n"
    "3. Call legal_agent with the brief to identify legal and compliance risks.\n"
    "4. Call writer_agent LAST, on its own, with one input that contains the brief, the research "
    "findings, the financial analysis, and the legal review. Its memo goes to the user as-is.\n"
    "For a follow-up question you can answer from the conversation so far, answer directly "
    "without calling the specialists again."
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
    return str(worker(f"Investment brief:\n{brief}\n\nMarket research:\n{research_context}"))


@tool
def legal_agent(brief: str) -> str:
    """Review legal and compliance risks: regulatory exposure, data privacy, IP, due diligence flags.

    Args:
        brief: The investment brief to review
    """
    worker = Agent(system_prompt=LEGAL_PROMPT, callback_handler=None)
    return str(worker(brief))


# The writer is an Agent turned into a tool with .as_tool(). delegate=True makes its memo
# the orchestrator's final answer: no extra orchestrator model call rewrites it, and the
# memo streams once through the orchestrator. preserve_context=False (the default) resets
# the writer before every call, like the fresh workers above.
writer = Agent(
    name="writer_agent",
    system_prompt=WRITER_PROMPT,
    callback_handler=None,
)
writer_agent = writer.as_tool(
    description=(
        "Write the final investment memo from the brief, research findings, financial analysis, "
        "and legal review. Call this LAST, after research_agent, finance_agent, and legal_agent."
    ),
    delegate=True,
)


def read_message(prompt: str) -> str:
    """Read one user message from the terminal.

    input() stops at the first newline, so a pasted multi-line brief would be
    sent as many separate turns. Pasted text arrives all at once, so every line
    already waiting on stdin is joined into the same message.
    Raises EOFError when stdin is closed.
    """
    if sys.platform == "win32":
        # select() only works on sockets on Windows: fall back to one line.
        return input(prompt).strip()
    print(prompt, end="", flush=True)
    fd = sys.stdin.fileno()
    data = os.read(fd, 65536)
    if not data:
        raise EOFError
    while select.select([fd], [], [], 0.1)[0]:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="replace").strip()


def main():
    print("Agent-as-Tool — Investment Analysis")
    print("Type or paste an investment brief (multi-line paste is one message), then ask follow-ups. Type 'quit' to exit.")
    print("Example: Investment brief for MarketNest Premium Tier: Option A $19.99/mo invite-only, B $14.99/mo 5% pilot, C $12.99/mo full launch. Target +15% CLV in 6 months. Budget $2M.\n")
    # One orchestrator for the whole conversation: it keeps its history, so follow-up
    # questions can build on the previous answers.
    orchestrator = Agent(
        tools=[research_agent, finance_agent, legal_agent, writer_agent],
        system_prompt=ORCHESTRATOR_PROMPT,
    )

    while True:
        try:
            user_input = read_message("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        print("\nRunning orchestrator (LLM delegates to Research, Finance, Legal, Writer)...")
        turn_start = len(orchestrator.messages)   # only report this turn's tool calls
        t0 = time.time()
        result = orchestrator(user_input)
        elapsed = time.time() - t0
        print(f"\nDone in {elapsed:.1f}s")

        print("\n=== ORCHESTRATOR TOOL CALLS ===")
        call_count = 0
        for msg in orchestrator.messages[turn_start:]:
            for block in msg["content"]:
                if "toolUse" in block:
                    tu = block["toolUse"]
                    call_count += 1
                    inp = json.dumps(tu["input"])
                    print(f"  {call_count}. {tu['name']}({inp[:80]}...)")
        print()
        print(f"Total tool calls: {call_count}")

        # Token usage
        summary = result.metrics.get_summary()
        usage = summary.get("accumulated_usage", {})
        print()
        print(f"{'Metric':<20} {'Value':>10}")
        print("-" * 32)
        print(f"{'Input tokens':<20} {usage.get('inputTokens', 0):>10,}")
        print(f"{'Output tokens':<20} {usage.get('outputTokens', 0):>10,}")
        print(f"{'Total tokens':<20} {usage.get('totalTokens', 0):>10,}")
        print(f"{'LLM cycles':<20} {summary.get('total_cycles', 'n/a'):>10}")
        print()

        tool_usage = summary.get("tool_usage", {})
        if tool_usage:
            print("Per-tool stats:")
            for name, data in tool_usage.items():
                s = data.get("execution_stats", {})
                print(f"  {name}: calls={s.get('call_count',0)} | avg_time={round(s.get('average_time',0),1)}s")
        print()


if __name__ == "__main__":
    main()
