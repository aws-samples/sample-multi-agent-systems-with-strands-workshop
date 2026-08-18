"""M2 Production: Sequential Chain on AgentCore Runtime.
Pattern: Research → Analyst → Synthesizer (Python code passes strings).

Local test:  python main.py
Deploy:      agentcore create → agentcore add → agentcore deploy
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent

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


RESEARCHER_PROMPT  = "You are a market research specialist. Use tools to gather data. Return structured findings."
ANALYST_PROMPT     = "You are a business analyst. Evaluate each option (A/B/C): strengths, weaknesses, complexity, top 2 risks+mitigations, verdict."
SYNTHESIZER_PROMPT = "Write a leadership memo: Recommendation, Options table A/B/C, Top 3 Risks, Success Metrics, Decision Required. Under 400 words."


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
    logger.info("session.id=%s module=m2-sequential-chain", _session_id)

    researcher  = Agent(tools=RESEARCH_TOOLS, system_prompt=RESEARCHER_PROMPT,  callback_handler=None)
    analyst     = Agent(system_prompt=ANALYST_PROMPT,    callback_handler=None)
    synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)

    research = researcher(f"Gather data for: {brief}")
    analysis = analyst(f"Brief:\n{brief}\n\nResearch:\n{research}")
    memo     = synthesizer(f"Brief:\n{brief}\n\nResearch:\n{research}\n\nAnalysis:\n{analysis}")

    return str(memo).strip()


if __name__ == "__main__":
    app.run()
