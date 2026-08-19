"""
Critic-Refiner Orchestrator (Pattern 3) — A2A + GraphBuilder.
researcher → critic_refiner (quality loop internal to specialist)
https://strandsagents.com/docs/user-guide/concepts/multi-agent/graph/
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
"""
import logging, os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands.agent.a2a_agent import A2AAgent
from strands.multiagent import GraphBuilder
from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

REGION             = os.environ.get("AWS_REGION", "us-east-1")
RESEARCHER_ARN     = os.environ["RESEARCHER_RUNTIME_ARN"]
CRITIC_REFINER_ARN = os.environ["CRITIC_REFINER_RUNTIME_ARN"]
ACTOR_HEADER       = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"
_pipelines: dict[str, "GraphBuilder"] = {}


def _current_session() -> tuple:
    import uuid
    headers = BedrockAgentCoreContext.get_request_headers() or {}
    return (BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4()),
            headers.get(ACTOR_HEADER) or "default-user")


def _make(arn, name, desc, aid) -> A2AAgent:
    a = A2AAgent(endpoint=a2a_endpoint(arn, REGION), client_config=make_a2a_config(aid, REGION),
                 name=name, description=desc)
    a._agent_card = build_agent_card(arn, name, desc, REGION)
    return a


def _get_pipeline(sid, aid):
    if sid not in _pipelines:
        researcher    = _make(RESEARCHER_ARN,     "researcher",    "Market research.", aid)
        critic_refiner = _make(CRITIC_REFINER_ARN, "critic_refiner", "Writer-Critic loop.", aid)
        b = GraphBuilder()
        b.add_node(researcher,     "researcher")
        b.add_node(critic_refiner, "critic_refiner")
        b.add_edge("researcher", "critic_refiner")
        b.set_execution_timeout(600)
        _pipelines[sid] = b
    return _pipelines[sid]


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    sid, aid = _current_session()
    result = _get_pipeline(sid, aid).build()(brief)
    for node in reversed(result.execution_order):
        if node.node_id == "critic_refiner":
            return str(node.result).strip()
    return str(result).strip()

if __name__ == "__main__":
    app.run()
