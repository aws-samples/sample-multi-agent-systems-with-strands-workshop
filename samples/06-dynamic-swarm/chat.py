"""Interactive chat for Module 6: Dynamic Swarm.

Runs the 4-agent swarm (Monitor, Network Specialist, DB Admin, Resolver)
for IT incident response. Agents hand off autonomously — no fixed routing.

    cd samples/06-dynamic-swarm
    pip install -r requirements.txt
    python chat.py

Type or paste an incident report and press Enter. A multi-line report pasted
at once (like INCIDENT_REPORT in the notebook) is sent as ONE message.
Type 'quit' or Ctrl+C to stop.
"""

import asyncio
import os
import select
import sys
import time
from strands import Agent
from strands.memory import MemoryManager
from strands.multiagent import Swarm
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


def read_message(prompt: str) -> str:
    """Read one user message from the terminal.

    input() stops at the first newline, so a pasted multi-line report would be
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


def build_swarm():
    # search_tool_config=False on every agent: memory is recalled through injection
    # only, so each agent keeps exactly the tools it has in the notebook.
    monitor = Agent(
        name="monitor",
        description=(
            "Entry point for all incidents. Detects symptoms, assesses impact, and classifies "
            "the incident type (network, database, or mixed). Routes to the right specialist first."
        ),
        system_prompt=(
            "You are a site reliability monitor. Analyze the incident report: identify symptoms, "
            "assess severity, classify whether this looks like a network/infra issue, a database issue, "
            "or both. Then hand off to the appropriate specialist (network_specialist or db_admin)."
        ),
        callback_handler=None,
        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False),
    )
    network_specialist = Agent(
        name="network_specialist",
        description=(
            "Investigates network and infrastructure root causes — load balancer health, CDN, "
            "DNS resolution, inter-service connectivity, TLS/cert issues. Consult me when the "
            "incident might be caused by network or infrastructure problems."
        ),
        system_prompt=(
            "You are a network specialist. Investigate the incident from a network and infrastructure "
            "angle: load balancer config, CDN cache, DNS, service mesh. Report your findings. "
            "If database involvement is suspected, hand off to db_admin. "
            "If investigation is complete, hand off to resolver."
        ),
        callback_handler=None,
        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False),
    )
    db_admin = Agent(
        name="db_admin",
        description=(
            "Investigates database root causes — slow queries, connection pool exhaustion, "
            "lock contention, index degradation, schema migration side effects. Consult me when "
            "DB metrics (connection pool, query latency, lock waits) are abnormal."
        ),
        system_prompt=(
            "You are a database administrator. Investigate the incident from a database angle: "
            "connection pool usage, slow query patterns, locks, recent schema changes from the deployment. "
            "Report your findings. Hand off to resolver when done."
        ),
        callback_handler=None,
        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False),
    )
    resolver = Agent(
        name="resolver",
        description=(
            "Synthesizes all specialist findings and produces the incident resolution plan with "
            "immediate actions, root cause summary, and prevention steps. Use me last."
        ),
        system_prompt=(
            "You are an incident resolver. Synthesize all findings from the team into a resolution plan:\n"
            "## Root Cause\n"
            "## Immediate Actions (ordered by priority)\n"
            "## Verification Steps\n"
            "## Prevention (what to change before next deployment)\n"
            "This is the FINAL step. Do NOT hand off to anyone else."
        ),
        callback_handler=None,
        memory_manager=MemoryManager(stores=[MEMORY], search_tool_config=False),
    )
    return Swarm(
        [monitor, network_specialist, db_admin, resolver],
        entry_point=monitor,        # monitor always starts the investigation
        max_handoffs=8,             # safety: 4 agents, up to 2 passes each
        max_iterations=12,
        execution_timeout=300.0,
        node_timeout=180.0,         # 180s per node — LLM calls on cold containers can take 90-120s
    )


def main():
    print("Dynamic Swarm — Incident Response")
    print("Type or paste an incident (multi-line paste is one message) and press Enter, then ask follow-ups.")
    print("The agents share a conversation memory. Type 'quit' to exit.")
    print("Example: Checkout API latency jumped from 450ms to 8s and 12% of requests return 5xx, 15 minutes after deployment v2.4.1; DB connection pool at 95%.\n")
    while True:
        try:
            user_input = read_message("Incident: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        swarm = build_swarm()
        print("\nRunning Swarm (no fixed path — agents route autonomously based on findings)...")
        t0 = time.time()
        result = swarm(user_input)
        total_time = time.time() - t0

        print(f"\nStatus: {result.status} | {total_time:.1f}s")
        print(f"Path emerged: {' → '.join(n.node_id for n in result.node_history)}")

        print("\n=== SWARM PATH ===")
        for i, node in enumerate(result.node_history):
            print(f"  {i+1}. {node.node_id}")

        print()
        # The Swarm's final response is the output of the last agent, the one that
        # ended without handing off. For a new incident that is the resolver (as in the
        # notebook); a follow-up can be answered and ended by an earlier agent.
        last = result.node_history[-1].node_id
        print(f"=== FINAL RESPONSE ({last} output) ===")
        print("-" * 60)
        print(str(result.results[last].result))
        print("-" * 60)
        remember(user_input, str(result.results[last].result).strip())

        # Token usage across the full swarm
        usage = result.accumulated_usage
        print()
        print(f"{'Metric':<20} {'Value':>10}")
        print("-" * 32)
        print(f"{'Input tokens':<20} {usage.get('inputTokens', 0):>10}")
        print(f"{'Output tokens':<20} {usage.get('outputTokens', 0):>10}")
        print(f"{'Total tokens':<20} {usage.get('totalTokens', 0):>10}")
        print(f"{'Agents in path':<20} {len(result.node_history):>10}")
        print(f"{'Execution time':<20} {total_time:>9.1f}s")
        print()


if __name__ == "__main__":
    main()
