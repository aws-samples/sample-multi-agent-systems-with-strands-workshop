"""M7 Production: Agent-as-Tool on AgentCore Runtime.
Pattern: LLM orchestrator with @tool specialist agents (Python code routing).

Local test:  python main.py
Deploy:      agentcore create → agentcore add → agentcore deploy
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

# ── Research tools ─────────────────────────────────────────────────────────
# Default: mock business intelligence tools, no setup needed.
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
SYNTHESIZER_PROMPT = "Write a leadership memo: Recommendation, Options table A/B/C, Top 3 Risks+mitigations, Success Metrics with targets, Decision Required. Under 400 words."
ORCHESTRATOR_PROMPT = (
    "Coordinate: 1.Call researcher_agent. 2.Call analyzer_agent three times (A, B, C) with research context. "
    "3.Call synthesizer_agent with all analyses. Execute all steps."
)


@tool
def researcher_agent(topic: str) -> str:
    '''Research market context: company data, benchmarks, and competitive intelligence.
    Args:
        topic: The decision topic to research
    '''
    worker = Agent(tools=RESEARCH_TOOLS, system_prompt=RESEARCHER_PROMPT, callback_handler=None)
    return str(worker(topic))


@tool
def analyzer_agent(option_name: str, option_description: str, research_context: str) -> str:
    '''Analyze one specific decision option. Call once per option (A, B, C).
    Args:
        option_name: Short name (e.g. "Option A")
        option_description: Full description with price and approach
        research_context: Research findings from researcher_agent
    '''
    worker = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    return str(worker(f"Option: {option_name}\nDesc: {option_description}\nResearch: {research_context}"))


@tool
def synthesizer_agent(decision_brief: str, all_analyses: str) -> str:
    '''Synthesize all option analyses into a leadership memo. Call AFTER all three analyses.
    Args:
        decision_brief: The original brief
        all_analyses: Combined analyses of all three options
    '''
    worker = Agent(system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)
    return str(worker(f"Brief:\n{decision_brief}\n\nAnalyses:\n{all_analyses}"))


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    # ── OTEL: propagate session ID across all spans ──────────────────
    import uuid as _uuid
    from opentelemetry import baggage as _baggage, context as _ctx
    _session_id = (context.session_id if context and hasattr(context, "session_id") else None) or str(_uuid.uuid4())
    _otel_ctx = _baggage.set_baggage("session.id", _session_id)
    _ctx.attach(_otel_ctx)
    logger.info("session.id=%s module=m7-agent-as-tool", _session_id)
    orchestrator = Agent(
        tools=[researcher_agent, analyzer_agent, synthesizer_agent],
        system_prompt=ORCHESTRATOR_PROMPT,
        callback_handler=None,
    )
    return str(orchestrator(brief)).strip()


if __name__ == "__main__":
    app.run()
