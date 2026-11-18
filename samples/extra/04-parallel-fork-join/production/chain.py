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
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status

from a2a_utils import a2a_endpoint, make_a2a_config

REGION = os.environ.get("AWS_REGION") or os.environ["RESEARCHER_RUNTIME_ARN"].split(":")[3]

DEFAULT_BRIEF = (
    "MarketNest Premium Tier: Options A ($19.99/mo invite-only), "
    "B ($14.99/mo 5% pilot), C ($12.99/mo full launch). "
    "Target: +15% CLV in 6 months. Budget: $2M."
)


class OptionAnalyzerNode(MultiAgentBase):
    """Graph node that sends one option assignment to the shared Analyzer runtime.

    The three analyzer nodes call the SAME runtime, and GraphBuilder hands every node the
    same input (brief + researcher findings). Locally each analyzer carries its option in
    its own system prompt; a deployed runtime has one fixed prompt, so this custom node
    (Graph "Custom Node Types") puts the assignment in front of the input it forwards to
    the A2AAgent.
    https://strandsagents.com/docs/user-guide/sdk/multi-agent/graph/
    """

    def __init__(self, agent: A2AAgent, option: str, name: str):
        super().__init__()
        self._agent = agent
        self.name = name
        self._assignment = (
            f"Your assignment: evaluate ONLY Option {option} from the brief below. "
            "Ignore the other options."
        )

    async def invoke_async(self, task, invocation_state=None, **kwargs):
        # Graph passes a str for entry nodes and a list of content blocks for dependent nodes.
        blocks = [{"text": task}] if isinstance(task, str) else list(task or [])
        result = await self._agent.invoke_async([{"text": self._assignment}, *blocks])
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(result=result, status=Status.COMPLETED)},
        )


def _make_agent(arn: str, name: str, description: str) -> A2AAgent:
    agent = A2AAgent(
        endpoint=a2a_endpoint(arn, REGION),
        client_config=make_a2a_config(region=REGION),
        name=name,
        description=description,
    )
    return agent


def run_chain(brief: str) -> str:
    """Run the fork-join chain and return the synthesizer's final memo."""
    researcher_arn  = os.environ["RESEARCHER_RUNTIME_ARN"]
    analyzer_arn    = os.environ["ANALYZER_RUNTIME_ARN"]
    synthesizer_arn = os.environ["SYNTHESIZER_RUNTIME_ARN"]
    researcher  = _make_agent(researcher_arn,  "researcher",  "Market research specialist.")
    # Same analyzer_arn used three times — parallel instances of the same specialist,
    # each told which option to evaluate (see OptionAnalyzerNode)
    analyzer_a  = OptionAnalyzerNode(_make_agent(analyzer_arn, "analyzer_a", "Option A analyst ($19.99/mo)."), "A", "analyzer_a")
    analyzer_b  = OptionAnalyzerNode(_make_agent(analyzer_arn, "analyzer_b", "Option B analyst ($14.99/mo)."), "B", "analyzer_b")
    analyzer_c  = OptionAnalyzerNode(_make_agent(analyzer_arn, "analyzer_c", "Option C analyst ($12.99/mo)."), "C", "analyzer_c")
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
