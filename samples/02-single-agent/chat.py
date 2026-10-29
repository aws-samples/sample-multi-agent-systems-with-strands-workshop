"""Interactive multi-turn chat for Module 2: Single Agent.

The notebook runs the agent one cell at a time. This script wraps the same
agent in a loop so you can hold a real multi-turn conversation in the terminal:
the agent keeps its context across turns.

From the cloned repo root:

    cd samples/02-single-agent
    pip install -r requirements.txt
    python chat.py

Type or paste your message and press Enter. A multi-line text pasted at once
(like the Situation Summary in the notebook) is sent as ONE message.
Type 'quit', 'exit', or Ctrl+C to stop.

Model: same as the notebook. To switch, change the model_id below to another
Amazon Bedrock model id (https://docs.aws.amazon.com/bedrock/latest/userguide/models-get-info.html).
"""

import os
import select
import sys

from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")


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

SYSTEM_PROMPT = '''

You are a senior Corporate Strategy Advisor.

You will receive a Situation Summary. Produce an Executive Strategy Briefing with:

1) Recommendation (1-2 lines)
2) Options considered (A/B/C)
3) Tradeoffs (bullets: gain vs risk)
4) Risks + mitigations (bullets)
5) Assumptions + unknowns (bullets)
6) Escalate? (Yes/No + reason)
7) Next steps (owner + timeline bullets)

Situation:
{Scenario}

Rules:
- Do not invent metrics. If missing, write "Unknown".
- Make tradeoffs explicit: "We gain X; we risk Y."
- If constraints are unmet or approvals missing, set Escalate=Yes.
- Keep sections in the same order.

'''



def main():
    # One Agent instance reused across all turns, its conversation history
    # lives in agent.messages, which is what makes it multi-turn.
    # context_manager="auto" keeps that growing history within the model's
    # context window automatically (summarises + offloads as it fills).
    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        model=model,
        context_manager="auto",
    )

    print("Strategy Advisor Agent  |  type 'quit' to exit")
    print("Type or paste a situation (multi-line paste is one message) and ask follow-ups. Type 'quit' to exit.")
    print("Example: We are considering a Premium Subscription Tier for MarketNest repeat buyers: A paid tier in metro zones, B lower-priced Plus tier, C convert loyalty members first. Decision in 2 weeks.\n")

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
