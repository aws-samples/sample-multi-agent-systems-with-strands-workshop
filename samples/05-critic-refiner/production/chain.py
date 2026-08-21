"""
Critic-Refiner coordinator — Pattern 3 demo.

Manages the Generator↔Critic loop using two separate A2A specialist runtimes:

  Writer Runtime  →  produces or revises the memo
  Critic Runtime  →  evaluates it: APPROVED or REVISION NEEDED: ...

The loop runs until the Critic says APPROVED or max_cycles is reached.
Context is passed explicitly in each A2A call — no shared in-process memory needed.

Required env vars (set by deploy.py or manually):
  WRITER_RUNTIME_ARN
  CRITIC_RUNTIME_ARN
  AWS_REGION (optional, defaults to us-east-1)

Usage:
  python chain.py                   # uses default demo brief
  python chain.py "your brief here"
"""
import asyncio
import os
import sys
import threading

from strands.agent.a2a_agent import A2AAgent

from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config, extract_a2a_text

REGION     = os.environ.get("AWS_REGION", "us-east-1")
MAX_CYCLES = 4

DEFAULT_BRIEF = (
    "NovaCart Premium Tier: Options A ($19.99/mo invite-only), "
    "B ($14.99/mo 5% pilot), C ($12.99/mo full launch). "
    "Target: +15% CLV in 6 months. Budget: $2M."
)


def _make_agent(arn: str, name: str, description: str) -> A2AAgent:
    agent = A2AAgent(
        endpoint=a2a_endpoint(arn, REGION),
        client_config=make_a2a_config(region=REGION),
        name=name,
        description=description,
    )
    agent._agent_card = build_agent_card(arn, name, description, REGION)
    return agent


def _call(agent: A2AAgent, prompt: str, timeout: int = 300) -> str:
    """Call an A2A agent in an isolated thread with a fresh event loop."""
    result_holder: list = [None, None]

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_holder[0] = loop.run_until_complete(agent.invoke_async(prompt))
        except Exception as exc:
            result_holder[1] = exc
        finally:
            loop.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        raise TimeoutError(f"A2A call timed out after {timeout}s")
    if result_holder[1] is not None:
        raise result_holder[1]
    return extract_a2a_text(result_holder[0])


def run_chain(brief: str) -> str:
    """Run the Generator↔Critic loop until APPROVED or MAX_CYCLES."""
    writer_arn = os.environ["WRITER_RUNTIME_ARN"]
    critic_arn = os.environ["CRITIC_RUNTIME_ARN"]
    writer = _make_agent(writer_arn, "writer", "Produces and revises the executive memo.")
    critic = _make_agent(critic_arn, "critic", "Evaluates the memo: APPROVED or REVISION NEEDED.")

    # Step 1: Writer produces the first draft
    draft = _call(writer, brief)

    for cycle in range(1, MAX_CYCLES + 1):
        # Step 2: Critic evaluates
        verdict = _call(critic, draft)
        print(f"  Cycle {cycle} — Critic: {verdict[:80].strip()}")

        if verdict.strip().upper().startswith("APPROVED"):
            return draft

        # Step 3: Writer revises — passes brief + previous draft + feedback explicitly
        revision_prompt = (
            f"Original brief:\n{brief}\n\n"
            f"Previous draft:\n{draft}\n\n"
            f"Revision required:\n{verdict}"
        )
        draft = _call(writer, revision_prompt)

    return draft  # return last draft if max cycles reached


if __name__ == "__main__":
    brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF
    print(f"\nRunning Critic-Refiner (2 separate runtimes)...\n{'─' * 60}")
    result = run_chain(brief)
    print(f"\n{'─' * 60}")
    print(result)
