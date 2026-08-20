"""
Sequential Chain coordinator — Pattern 1 demo.

Uses Strands GraphBuilder to call three remote A2A specialist runtimes
in fixed sequential order:

  Researcher → Analyst → Synthesizer

Each node's output becomes the next node's input — the chain.

This is intentionally simple Python code, not a deployed runtime.
For a deterministic pipeline with no LLM routing decisions, a lightweight
coordinator script is enough.

> NOTE — production alternatives for this coordination layer:
>   - AWS Lambda      : stateless, event-driven, no servers to manage
>   - AWS Step Functions : durable retries, execution history, visual workflow
>   - Amazon EventBridge Pipes : event-to-event sequential transformation
> The specialist AgentCore Runtimes (A2A protocol) stay unchanged in all cases.

Required env vars (set by deploy.py or manually):
  RESEARCHER_RUNTIME_ARN
  ANALYST_RUNTIME_ARN
  SYNTHESIZER_RUNTIME_ARN
  AWS_REGION (optional, defaults to us-east-1)

Usage:
  python chain.py                   # uses default demo brief
  python chain.py "your brief here"
"""
import os
import sys

from strands.agent.a2a_agent import A2AAgent
from strands.multiagent import GraphBuilder

from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config

REGION          = os.environ.get("AWS_REGION", "us-east-1")
RESEARCHER_ARN  = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYST_ARN     = os.environ["ANALYST_RUNTIME_ARN"]
SYNTHESIZER_ARN = os.environ["SYNTHESIZER_RUNTIME_ARN"]

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
    # Pre-populate agent card to skip unauthenticated discovery call
    agent._agent_card = build_agent_card(arn, name, description, REGION)
    return agent


def run_chain(brief: str) -> str:
    """Run Researcher → Analyst → Synthesizer and return the final memo."""
    researcher  = _make_agent(RESEARCHER_ARN,  "researcher",  "Market research specialist.")
    analyst     = _make_agent(ANALYST_ARN,     "analyst",     "Business strategy analyst.")
    synthesizer = _make_agent(SYNTHESIZER_ARN, "synthesizer", "Executive memo writer.")

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyst,     "analyst")
    builder.add_node(synthesizer, "synthesizer")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst",    "synthesizer")
    builder.set_execution_timeout(600)

    result = builder.build()(brief)

    for node in reversed(result.execution_order):
        if node.node_id == "synthesizer":
            return str(node.result).strip()
    return str(result).strip()


if __name__ == "__main__":
    brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF
    print(f"\nRunning Sequential Chain...\n{'─' * 60}")
    print(run_chain(brief))
