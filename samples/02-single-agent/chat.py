"""Interactive multi-turn chat for Module 2: Single Agent.

The notebook runs the agent one cell at a time. This script wraps the same
agent (same system prompt and tools) in a loop so you can hold a real
multi-turn conversation in the terminal: the agent keeps its context across turns.

From the cloned repo root:

    cd samples/02-single-agent
    pip install -r requirements.txt
    python chat.py

Type or paste your message and press Enter. A multi-line text pasted at once
(like DECISION_BRIEF in samples/shared/decision_brief.py) is sent as ONE message.
Type 'quit', 'exit', or Ctrl+C to stop.

Model: no model= is passed, so the agent uses the Strands default on Amazon Bedrock
(Claude Sonnet 4.6, global.anthropic.claude-sonnet-4-6). To switch, pass
model=BedrockModel(model_id="...") with another model enabled in your account.
"""

import os
import select
import sys

from strands import Agent
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data


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


SYSTEM_PROMPT = '''You are a senior Corporate Strategy Advisor for MarketNest.
Use your tools to look up company data, market benchmarks, and competitor information.
Never guess a number a tool can give you. If a metric is not available, write "Unknown".

For a quick question, answer in a few data-backed sentences.

For a full decision brief, produce an Executive Strategy Briefing with these sections, in order:
1) Recommendation (1-2 lines)
2) Options considered (A/B/C)
3) Tradeoffs: "We gain X; we risk Y."
4) Risks + mitigations
5) Assumptions + unknowns
6) Escalate? (Yes/No + reason; Yes if constraints are unmet or approvals are missing)
7) Next steps (owner + timeline)'''


def main():
    # One Agent instance reused across all turns, its conversation history
    # lives in agent.messages, which is what makes it multi-turn.
    # context_manager="auto" keeps that growing history within the model's
    # context window automatically (summarises + offloads as it fills).
    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        context_manager="auto",
    )

    print("Strategy Advisor Agent  |  type 'quit' to exit")
    print("Type or paste a decision brief or a question (multi-line paste is one message), then ask follow-ups.")
    print("Example: MarketNest Premium Tier: Option A $19.99/mo invite-only, B $14.99/mo 5% pilot, C $12.99/mo full launch. Target +15% CLV in 6 months. Budget $2M.\n")

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

        # The agent streams its response via the default callback handler.
        print("\nAgent: ", end="")
        agent(user_input)
        print()


if __name__ == "__main__":
    main()
