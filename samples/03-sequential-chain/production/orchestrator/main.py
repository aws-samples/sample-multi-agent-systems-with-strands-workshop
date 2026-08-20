"""
Sequential Chain Orchestrator — A2A Runtime (Pattern 1).

Uses Strands GraphBuilder with A2AAgent nodes in fixed sequential order:
  Researcher → Analyst → Synthesizer
Each node's output is the next node's input.

Strands GraphBuilder docs:
  https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/
AWS AgentCore A2A:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html

Per-session isolation: orchestrator + A2AAgents keyed by session_id
to prevent conversation history leaks across different users.
"""
import asyncio
import logging
import os
import threading

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands.agent.a2a_agent import A2AAgent
from strands.multiagent import GraphBuilder

from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config, extract_a2a_text

logger = logging.getLogger(__name__)
app    = BedrockAgentCoreApp()

REGION          = os.environ.get("AWS_REGION", "us-east-1")
RESEARCHER_ARN  = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYST_ARN     = os.environ["ANALYST_RUNTIME_ARN"]
SYNTHESIZER_ARN = os.environ["SYNTHESIZER_RUNTIME_ARN"]

ACTOR_HEADER = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"

# Per-session state — keyed by session_id
_pipelines: dict[str, "GraphBuilder"] = {}


def _current_session() -> tuple:
    import uuid
    headers    = BedrockAgentCoreContext.get_request_headers() or {}
    actor_id   = headers.get(ACTOR_HEADER) or "default-user"
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    return session_id, actor_id


def _make_a2a_agent(arn: str, name: str, description: str, actor_id: str) -> A2AAgent:
    agent = A2AAgent(
        endpoint=a2a_endpoint(arn, REGION),
        client_config=make_a2a_config(actor_id, REGION),
        name=name,
        description=description,
    )
    agent._agent_card = build_agent_card(arn, name, description, REGION)
    return agent


def _get_pipeline(sid: str, aid: str) -> GraphBuilder:
    """Build a GraphBuilder pipeline with A2AAgent nodes — one per session."""
    if sid not in _pipelines:
        researcher  = _make_a2a_agent(RESEARCHER_ARN,  "researcher",  "Market research specialist.", aid)
        analyst     = _make_a2a_agent(ANALYST_ARN,     "analyst",     "Business strategy analyst.", aid)
        synthesizer = _make_a2a_agent(SYNTHESIZER_ARN, "synthesizer", "Leadership memo writer.",    aid)

        builder = GraphBuilder()
        builder.add_node(researcher,  "researcher")
        builder.add_node(analyst,     "analyst")
        builder.add_node(synthesizer, "synthesizer")
        builder.add_edge("researcher",  "analyst")
        builder.add_edge("analyst",     "synthesizer")
        builder.set_execution_timeout(600)
        _pipelines[sid] = builder
    return _pipelines[sid]


@app.entrypoint
def invoke(payload, context):
    import time
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    sid, aid = _current_session()
    last_error = None
    for attempt in range(3):
        try:
            result = _get_pipeline(sid, aid).build()(brief)
            result_str = str(result).strip()
            if not result.execution_order or "Agent execution failed" in result_str:
                raise RuntimeError(f"Pipeline failed (cold start?): {result_str[:200]}")
            for node in reversed(result.execution_order):
                if node.node_id == "synthesizer":
                    return str(node.result).strip()
            return str(result).strip()
        except Exception as exc:
            last_error = exc
            _pipelines.pop(sid, None)
            logger.warning("Attempt %d failed: %s — retrying in %ds", attempt+1, exc, 10*(attempt+1))
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
    raise last_error


if __name__ == "__main__":
    app.run()
