"""M3 Production: Parallel Fork-Join on AgentCore Runtime.
Pattern: Researcher → [Analyzer A ∥ B ∥ C] → Synthesizer (asyncio.gather).

Local test:  python main.py
Deploy:      agentcore create → agentcore add → agentcore deploy
"""
import asyncio
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


RESEARCHER_PROMPT  = "Market research specialist. Use tools to gather data. Return structured findings."
ANALYZER_PROMPT    = "Business analyst. Evaluate the ONE option given: strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. 150 words max."
SYNTHESIZER_PROMPT = "Write a leadership memo: Recommendation, Options table A/B/C, Top 3 Risks, Success Metrics, Decision Required. Under 400 words."


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    researcher = Agent(tools=RESEARCH_TOOLS, system_prompt=RESEARCHER_PROMPT, callback_handler=None)
    research_text = str(researcher(f"Gather data for: {brief}"))

    a = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    b = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    c = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)

    async def fork():
        return await asyncio.gather(
            a.invoke_async(f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research_text}"),
            b.invoke_async(f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research_text}"),
            c.invoke_async(f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research_text}"),
        )

    ra, rb, rc = asyncio.run(fork())

    synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)
    memo = synthesizer(f"Brief:\n{brief}\n\nA:\n{ra}\n\nB:\n{rb}\n\nC:\n{rc}")
    return str(memo).strip()


if __name__ == "__main__":
    app.run()
