"""
Critic-Refiner coordinator — Pattern 3 demo.

Calls the remote Critic-Refiner specialist via A2A.
The specialist runs the Writer↔Critic GraphBuilder loop internally
and returns the approved memo.

This is intentionally simple Python code, not a deployed runtime.

> NOTE — production alternatives for this coordination layer:
>   - AWS Lambda      : stateless, event-driven, no servers to manage
>   - AWS Step Functions : durable execution with timeout handling
>   The specialist AgentCore Runtime (A2A protocol) stays unchanged in both cases.

Required env vars (set by deploy.py or manually):
  CRITIC_REFINER_RUNTIME_ARN
  AWS_REGION (optional, defaults to us-east-1)

Usage:
  python chain.py                   # uses default demo brief
  python chain.py "your brief here"
"""
import os
import sys

from strands.agent.a2a_agent import A2AAgent

from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config, extract_a2a_text

REGION             = os.environ.get("AWS_REGION", "us-east-1")
CRITIC_REFINER_ARN = os.environ["CRITIC_REFINER_RUNTIME_ARN"]

DEFAULT_BRIEF = (
    "NovaCart Premium Tier: Options A ($19.99/mo invite-only), "
    "B ($14.99/mo 5% pilot), C ($12.99/mo full launch). "
    "Target: +15% CLV in 6 months. Budget: $2M."
)


def run_chain(brief: str) -> str:
    """Send brief to the Critic-Refiner specialist and return the approved memo."""
    import asyncio, threading

    agent = A2AAgent(
        endpoint=a2a_endpoint(CRITIC_REFINER_ARN, REGION),
        client_config=make_a2a_config(region=REGION),
        name="critic_refiner",
        description="Writer-Critic quality loop.",
    )
    agent._agent_card = build_agent_card(
        CRITIC_REFINER_ARN, "critic_refiner", "Writer-Critic quality loop.", REGION
    )

    result_holder: list = [None, None]

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_holder[0] = loop.run_until_complete(agent.invoke_async(brief))
        except Exception as exc:
            result_holder[1] = exc
        finally:
            loop.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=600)
    if t.is_alive():
        raise TimeoutError("Critic-Refiner call timed out after 600s")
    if result_holder[1] is not None:
        raise result_holder[1]
    return extract_a2a_text(result_holder[0])


if __name__ == "__main__":
    brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF
    print(f"\nRunning Critic-Refiner...\n{'─' * 60}")
    print(run_chain(brief))
