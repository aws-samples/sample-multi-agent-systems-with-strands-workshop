"""M7 Production: Decision-Memo Capstone on AgentCore Runtime.
Patterns combined: P1 Sequential + P2 Fork-Join + P3 Critic-Refiner + P5 Agent-as-Tool.

Single Runtime (default): all patterns inside one container.
Multi-Runtime option: see README.md for deploying specialists as separate Runtimes.

Local test:  python main.py
Deploy:      agentcore create → agentcore add → agentcore deploy
"""
import asyncio
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
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


RESEARCHER_PROMPT  = "Market research specialist. Use tools to gather data. Return structured findings."
ANALYZER_PROMPT    = "Business analyst. Evaluate the ONE option given: strengths, weaknesses, complexity (Low/Med/High), top 2 risks+mitigations, verdict. 100 words max."
WRITER_PROMPT      = "Write a COMPLETE leadership memo: ## Recommendation, ## Options at a Glance (table A/B/C), ## Top 3 Risks+mitigations, ## Success Metrics (numeric targets), ## Decision Required. Revise if given feedback."
CRITIC_PROMPT      = "Check: 1)Recommendation 2)Options table A/B/C 3)3 Risks 4)2+ Metrics with targets 5)Decision Required. Respond: APPROVED or REVISION NEEDED: [criteria numbers]"
ORCHESTRATOR_PROMPT = "Coordinate: 1.researcher_agent 2.parallel_analyzers 3.critic_refiner. Execute all three in order."


@tool
def researcher_agent(topic: str) -> str:
    '''Research market context: company data, benchmarks, and competitive intelligence.
    Args:
        topic: The decision topic to research
    '''
    worker = Agent(tools=RESEARCH_TOOLS, system_prompt=RESEARCHER_PROMPT, callback_handler=None)
    return str(worker(topic))


@tool
def parallel_analyzers(brief: str, research_context: str) -> str:
    '''Run all three option analyzers (A, B, C) simultaneously. Use AFTER researcher_agent.
    Args:
        brief: The original decision brief
        research_context: Research findings from researcher_agent
    '''
    a = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    b = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)
    c = Agent(system_prompt=ANALYZER_PROMPT, callback_handler=None)

    async def fork():
        return await asyncio.gather(
            a.invoke_async(f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research_context}"),
            b.invoke_async(f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research_context}"),
            c.invoke_async(f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research_context}"),
        )

    ra, rb, rc = asyncio.run(fork())
    return f"OPTION A:\n{ra}\n\nOPTION B:\n{rb}\n\nOPTION C:\n{rc}"


@tool
def critic_refiner(brief: str, analyses: str) -> str:
    '''Draft and quality-check memo through GraphBuilder critic loop. Returns approved memo.
    Args:
        brief: The original brief
        analyses: Combined analyses from parallel_analyzers
    '''
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

    result = builder.build()(f"Brief:\n{brief}\n\nAnalyses:\n{analyses}")
    for node in reversed(result.execution_order):
        if node.node_id == "writer":
            return str(node.result).strip()
    return str(result).strip()


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
    logger.info("session.id=%s module=m7-capstone", _session_id)
    orchestrator = Agent(
        tools=[researcher_agent, parallel_analyzers, critic_refiner],
        system_prompt=ORCHESTRATOR_PROMPT,
        callback_handler=None,
    )
    return str(orchestrator(brief)).strip()


if __name__ == "__main__":
    app.run()
