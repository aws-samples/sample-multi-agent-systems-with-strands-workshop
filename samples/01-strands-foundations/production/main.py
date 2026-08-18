"""M1 Production: Decision Intelligence Agent on AgentCore Runtime.

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


SYSTEM_PROMPT = (
    "You are a Decision Intelligence Analyst. "
    "Use your tools to gather company data, benchmarks, and competitor intelligence. "
    "Always use tools — never guess when data is available."
)


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not prompt:
        raise ValueError("Missing required field: prompt")
    agent = Agent(tools=RESEARCH_TOOLS, system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return str(agent(prompt)).strip()


if __name__ == "__main__":
    app.run()
