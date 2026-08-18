"""M5 Production: Dynamic Swarm on AgentCore Runtime.
Pattern: Swarm with autonomous handoffs (single runtime — SDK manages shared context).

This Runtime also exposes an A2A endpoint (port 9000) for cross-framework orchestration.

Local test:  python main.py
Deploy:      agentcore create → agentcore add → agentcore deploy
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.multiagent import Swarm

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



@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    researcher = Agent(
        name="researcher",
        description="Market research specialist with tools for company data, benchmarks, and competitor intelligence. Use me first.",
        system_prompt="Use your tools to gather market data. Hand off to analyst when done.",
        tools=RESEARCH_TOOLS,
        callback_handler=None,
    )
    analyst = Agent(
        name="analyst",
        description="Business analyst who evaluates options A/B/C with structured analysis.",
        system_prompt="Evaluate options A/B/C: strengths, weaknesses, complexity, risks+mitigations, verdict. Hand off to writer.",
        callback_handler=None,
    )
    writer = Agent(
        name="writer",
        description="Executive memo writer. Produces the final leadership decision memo.",
        system_prompt="Write the final memo: Recommendation, Options table, Risks, Metrics, Decision Required. Do NOT hand off.",
        callback_handler=None,
    )

    swarm = Swarm([researcher, analyst, writer], entry_point=researcher,
                  max_handoffs=6, max_iterations=10, execution_timeout=180.0)
    result = swarm(brief)
    return str(result.results.get("writer", result)).strip()


if __name__ == "__main__":
    app.run()
