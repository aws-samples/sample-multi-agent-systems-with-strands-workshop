"""
Parallel Fork-Join coordinator — Pattern 2 demo.

Uses Strands GraphBuilder to call specialist runtimes with parallel execution:

  Researcher → [Analyzer A, Analyzer B, Analyzer C] → Synthesizer

The three analyzers run in parallel (fork); the synthesizer waits for all three
(join) and receives their combined outputs.

This is intentionally simple Python code, not a deployed runtime.

> NOTE — production alternatives for this coordination layer:
>   - AWS Lambda      : stateless, event-driven, no servers to manage
>   - AWS Step Functions : durable parallel branches with Map state
>   The specialist AgentCore Runtimes (A2A protocol) stay unchanged in all cases.

Required env vars (set by deploy.py or manually):
  RESEARCHER_RUNTIME_ARN
  ANALYZER_RUNTIME_ARN
  SYNTHESIZER_RUNTIME_ARN
  AWS_REGION (optional, defaults to the region in the runtime ARNs)

Usage:
  python chain.py                   # uses default demo brief
  python chain.py "your brief here"
"""
import os
import sys

from strands.agent.a2a_agent import A2AAgent
from strands.multiagent import GraphBuilder

from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config

REGION = os.environ.get("AWS_REGION") or os.environ["RESEARCHER_RUNTIME_ARN"].split(":")[3]

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


def run_chain(brief: str) -> str:
    """Run the fork-join chain and return the synthesizer's final memo."""
    researcher_arn  = os.environ["RESEARCHER_RUNTIME_ARN"]
    analyzer_arn    = os.environ["ANALYZER_RUNTIME_ARN"]
    synthesizer_arn = os.environ["SYNTHESIZER_RUNTIME_ARN"]
    researcher  = _make_agent(researcher_arn,  "researcher",  "Market research specialist.")
    # Same analyzer_arn used three times — parallel instances of the same specialist
    analyzer_a  = _make_agent(analyzer_arn, "analyzer_a", "Option A analyst ($19.99/mo).")
    analyzer_b  = _make_agent(analyzer_arn, "analyzer_b", "Option B analyst ($14.99/mo).")
    analyzer_c  = _make_agent(analyzer_arn, "analyzer_c", "Option C analyst ($12.99/mo).")
    synthesizer = _make_agent(synthesizer_arn, "synthesizer", "Executive memo writer.")

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyzer_a,  "analyzer_a")
    builder.add_node(analyzer_b,  "analyzer_b")
    builder.add_node(analyzer_c,  "analyzer_c")
    builder.add_node(synthesizer, "synthesizer")

    # Fork: researcher feeds all three analyzers in parallel
    builder.add_edge("researcher", "analyzer_a")
    builder.add_edge("researcher", "analyzer_b")
    builder.add_edge("researcher", "analyzer_c")
    # Join: synthesizer waits for all three analyzers
    builder.add_edge("analyzer_a", "synthesizer")
    builder.add_edge("analyzer_b", "synthesizer")
    builder.add_edge("analyzer_c", "synthesizer")
    builder.set_execution_timeout(600)

    result = builder.build()(brief)

    for node in reversed(result.execution_order):
        if node.node_id == "synthesizer":
            return str(node.result).strip()
    return str(result).strip()


if __name__ == "__main__":
    brief = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEF
    print(f"\nRunning Parallel Fork-Join...\n{'─' * 60}")
    print(run_chain(brief))
