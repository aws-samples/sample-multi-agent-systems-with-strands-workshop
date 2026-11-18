"""
Sequential Chain coordinator — Pattern 1 demo.

Uses Strands GraphBuilder to call three remote A2A specialist runtimes
in fixed sequential order:

  Researcher → Analyst → Synthesizer

Each node's output becomes the next node's input — the chain.

This is the same GraphBuilder chain as module-03.ipynb, but its nodes are
A2AAgent clients for the deployed runtimes: Strands graphs accept remote A2A
agents as nodes. chain.py runs locally; it is not a deployed runtime. For a
deterministic pipeline with no LLM routing decisions, that is enough.

> NOTE — production alternatives for this coordination layer:
>   - AWS Lambda      : stateless, event-driven, no servers to manage
>   - AWS Step Functions : durable retries, execution history, visual workflow
>   - Amazon EventBridge Pipes : event-to-event sequential transformation
> The specialist AgentCore Runtimes (A2A protocol) stay unchanged in all cases.

Required env vars (set by deploy.py or manually):
  RESEARCHER_RUNTIME_ARN
  ANALYST_RUNTIME_ARN
  SYNTHESIZER_RUNTIME_ARN
  AWS_REGION (optional, defaults to the region in the runtime ARNs)

Usage:
  python chain.py                   # uses the shared DECISION_BRIEF
  python chain.py "your brief here"
"""
import os
import sys

from strands.agent.a2a_agent import A2AAgent
from strands.multiagent import GraphBuilder

from a2a_utils import a2a_endpoint, make_a2a_config

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from decision_brief import DECISION_BRIEF

REGION = os.environ.get("AWS_REGION") or os.environ["RESEARCHER_RUNTIME_ARN"].split(":")[3]

DEFAULT_BRIEF = DECISION_BRIEF


def _make_agent(arn: str, name: str, description: str) -> A2AAgent:
    return A2AAgent(
        endpoint=a2a_endpoint(arn, REGION),
        client_config=make_a2a_config(region=REGION),
        name=name,
        description=description,
    )


def run_chain(brief: str) -> str:
    """Run Researcher → Analyst → Synthesizer and return the final memo."""
    researcher_arn  = os.environ["RESEARCHER_RUNTIME_ARN"]
    analyst_arn     = os.environ["ANALYST_RUNTIME_ARN"]
    synthesizer_arn = os.environ["SYNTHESIZER_RUNTIME_ARN"]
    researcher  = _make_agent(researcher_arn,  "researcher",  "Market research specialist.")
    analyst     = _make_agent(analyst_arn,     "analyst",     "Business strategy analyst.")
    synthesizer = _make_agent(synthesizer_arn, "synthesizer", "Executive memo writer.")

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyst,     "analyst")
    builder.add_node(synthesizer, "synthesizer")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst",    "synthesizer")
    builder.set_execution_timeout(600)

    result = builder.build()(brief)
    return str(result.results["synthesizer"].result).strip()


if __name__ == "__main__":
    brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF
    print(f"\nRunning Sequential Chain...\n{'─' * 60}")
    print(run_chain(brief))
