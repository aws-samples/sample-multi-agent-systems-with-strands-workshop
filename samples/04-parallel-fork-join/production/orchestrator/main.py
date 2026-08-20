"""
Parallel Fork-Join Orchestrator (Pattern 2) — A2A + GraphBuilder DAG.
researcher → [analyzer_a, analyzer_b, analyzer_c] → synthesizer
Same ANALYZER_ARN used 3x in parallel.
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

REGION          = os.environ.get("AWS_REGION", "us-east-1")
RESEARCHER_ARN  = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYZER_ARN    = os.environ["ANALYZER_RUNTIME_ARN"]
SYNTHESIZER_ARN = os.environ["SYNTHESIZER_RUNTIME_ARN"]
ACTOR_HEADER    = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"
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
        researcher  = _make(RESEARCHER_ARN,  "researcher",  "Market research.", aid)
        analyzer_a  = _make(ANALYZER_ARN, "analyzer_a", "Option A ($19.99/mo).", aid)
        analyzer_b  = _make(ANALYZER_ARN, "analyzer_b", "Option B ($14.99/mo).", aid)
        analyzer_c  = _make(ANALYZER_ARN, "analyzer_c", "Option C ($12.99/mo).", aid)
        synthesizer = _make(SYNTHESIZER_ARN, "synthesizer", "Memo writer.", aid)
        b = GraphBuilder()
        b.add_node(researcher, "researcher")
        b.add_node(analyzer_a, "analyzer_a")
        b.add_node(analyzer_b, "analyzer_b")
        b.add_node(analyzer_c, "analyzer_c")
        b.add_node(synthesizer, "synthesizer")
        b.add_edge("researcher", "analyzer_a")
        b.add_edge("researcher", "analyzer_b")
        b.add_edge("researcher", "analyzer_c")
        b.add_edge("analyzer_a", "synthesizer")
        b.add_edge("analyzer_b", "synthesizer")
        b.add_edge("analyzer_c", "synthesizer")
        b.set_execution_timeout(600)
        _pipelines[sid] = b
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
            _pipelines.pop(sid, None)  # clear stale cache; next attempt gets fresh agents
            logger.warning("Attempt %d failed: %s — retrying in %ds", attempt+1, exc, 10*(attempt+1))
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
    raise last_error

if __name__ == "__main__":
    app.run()
