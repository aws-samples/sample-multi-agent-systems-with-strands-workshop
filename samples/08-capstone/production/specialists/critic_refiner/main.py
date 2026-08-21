"""Critic-Refiner specialist — A2A Runtime (Capstone).
Runs the Writer→Critic GraphBuilder quality loop internally.
Called once by the orchestrator with brief + analyses.
Serves on port 9000. Returns the approved memo.

The critic_refiner_tool wraps the GraphBuilder loop so StrandsA2AExecutor
can call it via the standard Strands Agent interface.
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
"""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent, tool
from strands.multiagent import GraphBuilder
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

WRITER_PROMPT = (
    "Write a COMPLETE leadership memo with all 5 sections: "
    "## Recommendation, ## Options at a Glance (table A/B/C), ## Top 3 Risks+mitigations, "
    "## Success Metrics (numeric targets), ## Decision Required. Revise if given feedback."
)
CRITIC_PROMPT = (
    "Check: 1)Recommendation 2)Options table A/B/C 3)3 Risks+mitigations "
    "4)2+ Metrics with targets 5)Decision Required owner+deadline.\n"
    "Respond: APPROVED or REVISION NEEDED: [criteria numbers missing]"
)

_writer = None
_critic = None


def _get_writer() -> Agent:
    global _writer
    if _writer is None:
        _writer = Agent(name="writer", system_prompt=WRITER_PROMPT, callback_handler=None)
    return _writer


def _get_critic() -> Agent:
    global _critic
    if _critic is None:
        _critic = Agent(name="critic", system_prompt=CRITIC_PROMPT, callback_handler=None)
    return _critic


@tool
def run_writer_critic_loop(brief_and_analyses: str) -> str:
    """Run the Writer-Critic quality loop on the given brief and analyses.
    Call immediately with the complete input.
    Args:
        brief_and_analyses: The full input including brief and analyses to process.
    """
    def needs_revision(state):
        r = state.results.get("critic")
        return bool(r) and "revision needed" in str(r.result).lower()

    builder = GraphBuilder()
    builder.add_node(_get_writer(), "writer")
    builder.add_node(_get_critic(), "critic")
    builder.set_entry_point("writer")
    builder.add_edge("writer", "critic")
    builder.add_edge("critic", "writer", condition=needs_revision)
    builder.set_max_node_executions(6)
    builder.set_execution_timeout(120)
    builder.reset_on_revisit(True)

    result = builder.build()(brief_and_analyses)
    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            return str(node.result).strip()
    return str(result).strip()


_pipeline_agent = None


def get_pipeline_agent() -> Agent:
    """Wrapper Agent that drives the internal GraphBuilder loop via a tool."""
    global _pipeline_agent
    if _pipeline_agent is None:
        _pipeline_agent = Agent(
            tools=[run_writer_critic_loop],
            system_prompt=(
                "You receive a decision brief and analyses. "
                "Immediately call run_writer_critic_loop with the complete input. "
                "Do not paraphrase or summarize — pass the full input as-is."
            ),
            callback_handler=None,
        )
    return _pipeline_agent


if __name__ == "__main__":
    # This file runs on Amazon Bedrock AgentCore Runtime — not locally.
    # Running it locally starts a server on port 9000 that requires
    # AgentCore authentication to work. Deploy with deploy.py instead.
    serve_a2a(StrandsA2AExecutor(get_pipeline_agent()))
