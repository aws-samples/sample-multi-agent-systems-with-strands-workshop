"""Interactive chat for Module 4: Parallel / Fork-Join.

Uses GraphBuilder parallel topology: the Strands-native way to run agents
in parallel. No asyncio needed: the SDK handles execution.

    cd samples/04-parallel-fork-join
    uv pip install -r requirements.txt
    uv run python chat.py

Type or paste a decision brief and press Enter. A multi-line brief pasted at
once (like DECISION_BRIEF in the notebook) is sent as ONE message.
Type 'quit' or Ctrl+C to stop.

Model options (pass model= to each Agent to switch):
    from strands.models import BedrockModel
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")  # default
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")   # AWS credits
"""

import asyncio
import sys, os, time, select
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

RESEARCHER_PROMPT = (
    "You are a market research specialist. Use your tools to gather relevant data. "
    "Return structured findings. data only, no recommendations."
)

# Each Analyzer has a different option assigned in its prompt
# GraphBuilder passes the Researcher findings automatically in the context
ANALYZER_A_PROMPT = (
    "You are a business analyst. Evaluate Option A ($19.99/mo, invite-only top 10% spenders) "
    "based on the decision brief and research context provided. "
    "Return: strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. "
    "150 words max."
)
ANALYZER_B_PROMPT = (
    "You are a business analyst. Evaluate Option B ($14.99/mo, 5% A/B pilot with kill-switch) "
    "based on the decision brief and research context provided. "
    "Return: strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. "
    "150 words max."
)
ANALYZER_C_PROMPT = (
    "You are a business analyst. Evaluate Option C ($12.99/mo, full launch, 30-day trial) "
    "based on the decision brief and research context provided. "
    "Return: strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. "
    "150 words max."
)

SYNTHESIZER_PROMPT = (
    "You are an executive communications specialist. Write a leadership memo from all analyses:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table comparing A, B, C)\n"
    "## Top 3 Risks with mitigations\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, approvers)\n"
    "Under 400 words."
)


def build_graph():
    # search_tool_config=False: memory is recalled through injection only, so each
    # agent keeps exactly the tools it has in the notebook.
    researcher  = Agent(name="researcher",  system_prompt=RESEARCHER_PROMPT,
                        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
                        callback_handler=None,
                        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))
    analyzer_a  = Agent(name="analyzer_a",  system_prompt=ANALYZER_A_PROMPT, callback_handler=None,
                        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))
    analyzer_b  = Agent(name="analyzer_b",  system_prompt=ANALYZER_B_PROMPT, callback_handler=None,
                        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))
    analyzer_c  = Agent(name="analyzer_c",  system_prompt=ANALYZER_C_PROMPT, callback_handler=None,
                        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))
    synthesizer = Agent(name="synthesizer", system_prompt=SYNTHESIZER_PROMPT, callback_handler=None,
                        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False))

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyzer_a,  "analyzer_a")
    builder.add_node(analyzer_b,  "analyzer_b")
    builder.add_node(analyzer_c,  "analyzer_c")
    builder.add_node(synthesizer, "synthesizer")

    builder.add_edge("researcher", "analyzer_a")
    builder.add_edge("researcher", "analyzer_b")
    builder.add_edge("researcher", "analyzer_c")
    builder.add_edge("analyzer_a", "synthesizer")
    builder.add_edge("analyzer_b", "synthesizer")
    builder.add_edge("analyzer_c", "synthesizer")

    builder.set_execution_timeout(300)
    return builder.build()


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
    print("Parallel Fork-Join (GraphBuilder)")
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

        graph = build_graph()

        print("\nRunning GraphBuilder parallel Fork-Join...")
        t0 = time.time()
        result = graph(user_input)
        elapsed = time.time() - t0

        path = [n.node_id for n in result.execution_order]
        print(f"\nStatus: {result.status} | {elapsed:.1f}s")
        print(f"Execution order: {' → '.join(path)}")
        print()
        for node in reversed(result.execution_order):
            if node.node_id == "synthesizer":
                print("─" * 60)
                print(str(node.result))
                print("─" * 60)
                remember(user_input, str(node.result).strip())
                break
        print()


if __name__ == "__main__":
    main()
