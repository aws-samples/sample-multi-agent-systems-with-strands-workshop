"""M4 Production: Critic-Refiner on AgentCore Runtime.
Pattern: GraphBuilder Writer + Critic quality loop (single runtime — SDK manages cycle state).

Local test:  python main.py
Deploy:      agentcore create → agentcore add → agentcore deploy
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.multiagent import GraphBuilder

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

# ── Research tools ─────────────────────────────────────────────────────────
# Default: mock business intelligence tools — no setup needed.
# Optional: replace with AgentCore Web Search for live market data:
#
#   from strands.tools.mcp.mcp_client import MCPClient
#   from mcp.client.streamable_http import streamablehttp_client
#   GATEWAY_URL = os.environ["GATEWAY_URL"]   # AgentCore Gateway with Web Search connector
#
#   with MCPClient(lambda: streamablehttp_client(GATEWAY_URL)) as client:
#       tools = client.list_tools_sync()
#       agent = Agent(tools=tools, ...)
#
# See: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html
from mock_tools import get_company_data, get_market_benchmarks, get_competitor_data

RESEARCH_TOOLS = [get_company_data, get_market_benchmarks, get_competitor_data]


RESEARCHER_PROMPT = "Market research specialist. Use tools to gather data. Return structured findings."
WRITER_PROMPT = (
    "Write a COMPLETE leadership memo with all 5 sections: "
    "## Recommendation, ## Options at a Glance (table A/B/C), ## Top 3 Risks+mitigations, "
    "## Success Metrics (numeric targets), ## Decision Required (owner+deadline). "
    "If given feedback, revise."
)
CRITIC_PROMPT = (
    "Check ONLY: 1)Recommendation 2)Options table A/B/C 3)3 Risks+mitigations "
    "4)2+ Metrics with targets 5)Decision Required owner+deadline.\n"
    "Respond: APPROVED or REVISION NEEDED: [criteria numbers missing]"
)


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    # ── OTEL: propagate session ID across all spans ──────────────────
    import uuid as _uuid
    from opentelemetry import baggage as _baggage, context as _ctx
    _session_id = (payload.get("session_id") if isinstance(payload, dict) else None) or str(_uuid.uuid4())
    _otel_ctx = _baggage.set_baggage("session.id", _session_id)
    _ctx.attach(_otel_ctx)
    logger.info("session.id=%s module=m4-critic-refiner", _session_id)

    researcher = Agent(tools=RESEARCH_TOOLS, system_prompt=RESEARCHER_PROMPT, callback_handler=None)
    research_text = str(researcher(f"Gather data for: {brief}"))

    writer = Agent(name="writer", system_prompt=WRITER_PROMPT, callback_handler=None)
    critic = Agent(name="critic", system_prompt=CRITIC_PROMPT, callback_handler=None)

    def needs_revision(state):
        r = state.results.get("critic")
        return bool(r) and "revision needed" in str(r.result).lower()

    builder = GraphBuilder()
    builder.add_node(writer, "writer")
    builder.add_node(critic, "critic")
    builder.set_entry_point("writer")
    builder.add_edge("writer", "critic")
    builder.add_edge("critic", "writer", condition=needs_revision)
    builder.set_max_node_executions(6)
    builder.set_execution_timeout(120)
    builder.reset_on_revisit(True)

    result = builder.build()(f"Brief:\n{brief}\n\nResearch:\n{research_text}")
    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            return str(node.result).strip()
    return str(result).strip()


if __name__ == "__main__":
    app.run()
