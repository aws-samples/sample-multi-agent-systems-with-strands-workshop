"""Interactive chat for Module 5: Critic-Refiner.

Uses Strands GraphBuilder with a cycle edge:
  Writer drafts → Critic evaluates → REVISION NEEDED loops back → APPROVED exits

    cd samples/05-critic-refiner
    uv pip install -r requirements.txt
    uv run python chat.py

Type or paste a decision brief and press Enter. A multi-line brief pasted at
once (like DECISION_BRIEF in the notebook) is sent as ONE message.
Type 'quit' or Ctrl+C to stop.
"""

import asyncio
import os
import select
import sys
import time

from strands import Agent
from strands.memory import MemoryManager
from strands.multiagent import GraphBuilder
from strands.vended_memory_stores.test_memory_store import TestMemoryStore

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

WRITER_PROMPT = (
    "You are an executive memo writer. Write a COMPLETE leadership memo with exactly these 5 labeled sections:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table comparing A, B, C on Complexity/Risk/Verdict)\n"
    "## Top 3 Risks (each risk with a specific mitigation action)\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, who must approve)\n"
    "If you receive feedback, revise and include ALL 5 sections in the new version."
)

CRITIC_PROMPT = (
    "You are a quality critic. Check ONLY these 5 criteria:\n"
    "1. '## Recommendation' section with a clear option choice (A, B, or C)\n"
    "2. '## Options at a Glance' table comparing A, B, C\n"
    "3. '## Top 3 Risks' with at least 3 risks each with a specific mitigation\n"
    "4. '## Success Metrics' with at least 2 KPIs that have numeric targets\n"
    "5. '## Decision Required' with both owner AND deadline\n"
    "DO NOT check for research data, background context, or any section not listed.\n"
    "Respond with EXACTLY one of:\n"
    "APPROVED\n"
    "(if all 5 criteria are met)\n"
    "REVISION NEEDED: [which criterion numbers are missing or incomplete]\n"
    "Your response must start with APPROVED or REVISION NEEDED."
)


def build_graph():
    """Build the Critic-Refiner graph (same topology and limits as the notebook)."""
    # search_tool_config=False: memory is recalled through injection only, so the
    # agents keep exactly the tools they have in the notebook (none).
    writer = Agent(name="writer", system_prompt=WRITER_PROMPT, callback_handler=None,
                   memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))
    critic = Agent(name="critic", system_prompt=CRITIC_PROMPT, callback_handler=None,
                   memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

    def needs_revision(state):
        '''Returns True if the Critic said REVISION NEEDED.'''
        r = state.results.get("critic")
        return bool(r) and "revision needed" in str(r.result).lower()

    builder = GraphBuilder()
    builder.add_node(writer, "writer")
    builder.add_node(critic, "critic")
    builder.set_entry_point("writer")
    builder.add_edge("writer", "critic")
    builder.add_edge("critic", "writer", condition=needs_revision)
    builder.set_max_node_executions(8)
    builder.set_execution_timeout(180)
    builder.reset_on_revisit(True)
    return builder.build()


def run_critic_refiner(brief: str) -> None:
    """Run one turn of the conversation through a fresh Critic-Refiner graph."""
    t0 = time.time()
    result = build_graph()(brief)
    elapsed = time.time() - t0

    print(f"\nStatus: {result.status} | {elapsed:.1f}s")
    print(f"Execution order: {[n.node_id for n in result.execution_order]}")
    print()

    # Show each Critic verdict
    for node in result.execution_order:
        if node.node_id == "critic":
            verdict = str(node.result)[:120].strip()
            print(f"  Critic verdict: {verdict}")

    # Print the final approved memo
    print("─" * 60)
    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            print(str(node.result))
            remember(brief, str(node.result).strip())
            break
    print("─" * 60)

    writer_runs = sum(1 for n in result.execution_order if n.node_id == "writer")
    critic_runs = sum(1 for n in result.execution_order if n.node_id == "critic")
    print(f"Writer drafts: {writer_runs} | Critic reviews: {critic_runs}")


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
    print("Critic-Refiner — Strands GraphBuilder cycle")
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

        print("\nRunning Writer → Critic loop...")
        run_critic_refiner(user_input)
        print()


if __name__ == "__main__":
    main()
