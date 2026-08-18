"""M3 Production: Parallel Fork-Join: GraphBuilder parallel topology.
Pattern: Researcher → [Analyzer A ∥ B ∥ C] → Synthesizer
Uses GraphBuilder (Strands-native), not asyncio.gather.

Local test:  python main.py
Deploy:      agentcore create → agentcore add → agentcore deploy
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.multiagent import GraphBuilder

from mock_tools import get_company_data, get_market_benchmarks, get_competitor_data

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

RESEARCH_TOOLS = [get_company_data, get_market_benchmarks, get_competitor_data]

RESEARCHER_PROMPT  = "Market research specialist. Use tools to gather data. Return structured findings."
ANALYZER_A_PROMPT  = "Evaluate Option A ($19.99 invite-only) from brief+research. Strengths, weaknesses, complexity, top 2 risks, verdict."
ANALYZER_B_PROMPT  = "Evaluate Option B ($14.99 5% pilot) from brief+research. Strengths, weaknesses, complexity, top 2 risks, verdict."
ANALYZER_C_PROMPT  = "Evaluate Option C ($12.99 full launch) from brief+research. Strengths, weaknesses, complexity, top 2 risks, verdict."
SYNTHESIZER_PROMPT = "Write memo: Recommendation, Options table A/B/C, Top 3 Risks, Success Metrics, Decision Required. Under 400 words."

# OTEL session propagation
import uuid as _uuid
from opentelemetry import baggage as _baggage, context as _ctx


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    # OTEL session propagation
    _session_id = (payload.get("session_id") if isinstance(payload, dict) else None) or str(_uuid.uuid4())
    _token = _ctx.attach(_baggage.set_baggage("session.id", _session_id))
    logger.info("session.id=%s module=m3-parallel-fork-join", _session_id)

    researcher  = Agent(tools=RESEARCH_TOOLS, system_prompt=RESEARCHER_PROMPT,  callback_handler=None)
    analyzer_a  = Agent(system_prompt=ANALYZER_A_PROMPT, callback_handler=None)
    analyzer_b  = Agent(system_prompt=ANALYZER_B_PROMPT, callback_handler=None)
    analyzer_c  = Agent(system_prompt=ANALYZER_C_PROMPT, callback_handler=None)
    synthesizer = Agent(system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyzer_a,  "analyzer_a")
    builder.add_node(analyzer_b,  "analyzer_b")
    builder.add_node(analyzer_c,  "analyzer_c")
    builder.add_node(synthesizer, "synthesizer")
    builder.add_edge("researcher", "analyzer_a")
    builder.add_edge("researcher", "analyzer_b")
    builder.add_edge("researcher", "analyzer_c")
    builder.add_edge("analyzer_a", "synthesizer")
    builder.add_edge("analyzer_b", "synthesizer")
    builder.add_edge("analyzer_c", "synthesizer")
    builder.set_execution_timeout(300)

    result = builder.build()(brief)

    _ctx.detach(_token)

    for node in reversed(result.execution_order):
        if node.node_id == "synthesizer":
            return str(node.result).strip()
    return str(result).strip()


if __name__ == "__main__":
    app.run()
