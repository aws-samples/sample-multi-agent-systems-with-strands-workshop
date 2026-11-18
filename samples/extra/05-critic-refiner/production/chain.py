"""
Critic-Refiner coordinator — Pattern 3 demo.

Manages the Generator↔Critic loop using two separate A2A specialist runtimes:

  Writer Runtime  →  produces or revises the memo
  Critic Runtime  →  evaluates it: APPROVED or REVISION NEEDED: ...

The loop runs until the Critic says APPROVED or max_cycles is reached.
Context is passed explicitly in each A2A call — no shared in-process memory needed.

Why an explicit loop here (and not a GraphBuilder cycle):
  A GraphBuilder cycle drives its nodes in one process. In this deployment the
  Writer and Critic are *separate* AgentCore Runtimes reached over A2A, so the
  coordinator lives outside both and threads context between them by hand. The
  single-runtime variant `main.py` uses the native GraphBuilder cycle instead —
  compare the two to see when each is the right fit.

Required env vars (set by deploy.py or manually):
  WRITER_RUNTIME_ARN
  CRITIC_RUNTIME_ARN
  AWS_REGION (optional, defaults to the region in the runtime ARNs)

Usage:
  python chain.py                   # uses default demo brief
  python chain.py "your brief here"
"""
import asyncio
import os
import sys
import threading

from strands.agent.a2a_agent import A2AAgent

from a2a_utils import a2a_endpoint, make_a2a_config, extract_a2a_text

REGION     = os.environ.get("AWS_REGION") or os.environ["WRITER_RUNTIME_ARN"].split(":")[3]
MAX_CYCLES = 4

DEFAULT_BRIEF = (
    "MarketNest Premium Tier: Options A ($19.99/mo invite-only), "
    "B ($14.99/mo 5% pilot), C ($12.99/mo full launch). "
    "Target: +15% CLV in 6 months. Budget: $2M."
)


def _make_agent(arn: str, name: str, description: str) -> tuple:
    """Return (A2AAgent, httpx client). The client is closed by run_chain when done."""
    config = make_a2a_config(region=REGION)
    # client_config's httpx client (SigV4) is used for both agent-card discovery and
    # message sending, so A2AAgent resolves the card itself - no private attributes.
    agent = A2AAgent(
        endpoint=a2a_endpoint(arn, REGION),
        client_config=config,
        name=name,
        description=description,
    )
    return agent, config.httpx_client


async def _call(agent: A2AAgent, prompt: str, timeout: int = 300) -> str:
    """Call an A2A agent (must run on the same event loop as the rest of the chain)."""
    return extract_a2a_text(await asyncio.wait_for(agent.invoke_async(prompt), timeout=timeout))


async def _run_chain_async(brief: str) -> str:
    writer_arn = os.environ["WRITER_RUNTIME_ARN"]
    critic_arn = os.environ["CRITIC_RUNTIME_ARN"]
    writer, writer_http = _make_agent(writer_arn, "writer", "Produces and revises the executive memo.")
    critic, critic_http = _make_agent(critic_arn, "critic", "Evaluates the memo: APPROVED or REVISION NEEDED.")

    try:
        # Step 1: Writer produces the first draft
        draft = await _call(writer, brief)

        for cycle in range(1, MAX_CYCLES + 1):
            # Step 2: Critic evaluates
            verdict = await _call(critic, draft)
            print(f"  Cycle {cycle} — Critic: {verdict[:80].strip()}")

            if verdict.strip().upper().startswith("APPROVED"):
                return draft

            # Step 3: Writer revises — passes brief + previous draft + feedback explicitly
            revision_prompt = (
                f"Original brief:\n{brief}\n\n"
                f"Previous draft:\n{draft}\n\n"
                f"Revision required:\n{verdict}"
            )
            draft = await _call(writer, revision_prompt)

        return draft  # return last draft if max cycles reached
    finally:
        # Close the pooled HTTP connections on the loop that opened them.
        await writer_http.aclose()
        await critic_http.aclose()


def run_chain(brief: str) -> str:
    """Run the Generator↔Critic loop until APPROVED or MAX_CYCLES.

    The whole loop runs on ONE event loop in an isolated thread (so it also works
    inside Jupyter, which already has a running loop). All A2A calls must share
    that loop: each A2AAgent reuses one pooled httpx client, and a client used
    after its loop was closed fails with "Event loop is closed" on the 2nd call.
    """
    holder: list = [None, None]

    def _run():
        try:
            holder[0] = asyncio.run(_run_chain_async(brief))
        except BaseException as exc:  # re-raised in the caller's thread
            holder[1] = exc

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join()
    if holder[1] is not None:
        raise holder[1]
    return holder[0]


if __name__ == "__main__":
    brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF
    print(f"\nRunning Critic-Refiner (2 separate runtimes)...\n{'─' * 60}")
    result = run_chain(brief)
    print(f"\n{'─' * 60}")
    print(result)
