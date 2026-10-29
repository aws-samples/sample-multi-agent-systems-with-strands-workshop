"""Interactive chat for Module 3: Sequential Chain.

Uses the Strands Graph primitive (GraphBuilder) to run the 3-stage pipeline:
  Researcher → Analyst → Synthesizer

Each node's output becomes the next node's input — the chain.
GraphBuilder is the Strands primitive for deterministic multi-agent graphs.

    cd samples/03-sequential-chain
    uv pip install -r requirements.txt
    uv run python chat.py

Type or paste a decision brief and press Enter. A multi-line brief pasted at
once (like DECISION_BRIEF in the notebook) is sent as ONE message.
Type 'quit' or Ctrl+C to stop.

Model options (pass model= to each Agent to switch):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")  # default
    model = BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # AWS credits
    model = BedrockModel(model_id="amazon.nova-lite-v1:0")  # cheapest
"""

import asyncio
import sys
import os
import select
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "02-single-agent"))

from strands import Agent
from strands.memory import MemoryManager
from strands.multiagent import GraphBuilder
from strands.vended_memory_stores.test_memory_store import TestMemoryStore
from decision_brief_tools import get_company_data, get_market_benchmarks, get_competitor_data

# Conversation memory for this chat session (Strands memory: TestMemoryStore + MemoryManager).
# Only two things are saved per turn: what the user said and the system's final answer,
# written with the store's documented add() once the turn ends. Nothing the agents say to
# each other is stored. Every turn builds fresh agents, exactly like the notebook, and each
# agent reads this memory through its own MemoryManager: injection adds the relevant
# entries to its model input before each call. Inside a turn the agents still pass work
# only through the pattern itself. persist=False: nothing is written to disk.
MEMORY = TestMemoryStore(name="conversation", persist=False)


def remember(user_message: str, final_answer: str) -> None:
    """Save one turn of the conversation: the user's message and the final answer."""
    async def save():
        await MEMORY.add(f"User: {user_message}", {"role": "user"})
        await MEMORY.add(f"Final answer: {final_answer}", {"role": "final_answer"})
    asyncio.run(save())

RESEARCHER_PROMPT = '''You are a market research specialist.
Given a decision brief, gather relevant company data, market benchmarks,
and competitor intelligence using your tools.
Return structured findings. data only, no recommendations.'''

ANALYST_PROMPT = '''You are a business strategy analyst.
Given market research findings and a decision brief, analyze each option (A, B, C).
For each option return:
- Strengths and weaknesses
- Implementation complexity: Low / Medium / High (with one-sentence justification)
- Top 2 risks with specific mitigations
- Verdict: Proceed / Proceed with caution / Do not proceed
Return structured analysis only. no executive memo yet.'''

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
### Success Metrics (3-5 KPIs with targets)
### Decision Required: owner · deadline · approvers needed

Under 400 words. Be direct.'''


def build_chain():
    """Build the sequential chain via Strands GraphBuilder (same as the notebook)."""
    researcher = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT,
        callback_handler=None,
        # search_tool_config=False: recall happens through injection only, so the
        # agent keeps exactly the tools it has in the notebook.
        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False),
    )
    analyst     = Agent(system_prompt=ANALYST_PROMPT,     callback_handler=None,
                        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))
    synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT, callback_handler=None,
                        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyst,     "analyst")
    builder.add_node(synthesizer, "synthesizer")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst",    "synthesizer")
    builder.set_execution_timeout(300)   # stop a runaway graph (Strands warns when no limit is set)
    return builder.build()


def run_chain(brief: str) -> str:
    """Run one turn of the conversation through a fresh chain and return the memo."""
    result = build_chain()(brief)

    for node in reversed(result.execution_order):
        if node.node_id == "synthesizer":
            return str(node.result).strip()
    return str(result).strip()


def read_message(prompt: str) -> str:
    """Read one user message from the terminal.

    input() stops at the first newline, so a pasted multi-line brief would be
    sent as many separate runs. Pasted text arrives all at once, so every line
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
    print("Sequential Chain — Strands Graph (GraphBuilder)")
    print("Type or paste a decision brief (multi-line paste is one message) and press Enter, then ask follow-ups.")
    print("The agents share a conversation memory. Type 'quit' to exit.")
    print("Example: MarketNest Premium Tier: Option A $19.99/mo invite-only, B $14.99/mo 5% pilot, C $12.99/mo full launch. Target +15% CLV in 6 months. Budget $2M.\n")

    while True:
        try:
            user_input = read_message("Brief: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        print("\nRunning Researcher → Analyst → Synthesizer (about a minute)...\n")
        memo = run_chain(user_input)
        print(memo)
        remember(user_input, memo)
        print("\n" + "─" * 60 + "\n")


if __name__ == "__main__":
    main()
