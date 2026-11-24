"""Module 3 production, single-runtime variant: Sequential Chain on AgentCore Runtime.

Pattern: Researcher → Analyst → Synthesizer, the same graph, prompts and timeout as
module-03.ipynb, served as ONE AgentCore HTTP runtime. All three agents run in this
process; the Strands Graph (GraphBuilder) passes each node's output to the next.

deploy.py does not deploy this file: it deploys the three specialists as separate A2A
runtimes and chain.py coordinates them with the same GraphBuilder and A2AAgent nodes.
Use this file when you want the whole chain behind one endpoint instead.

Local test:  python main.py   (serves the AgentCore HTTP contract on port 8080)
"""
import logging
import uuid

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from opentelemetry import baggage, context as otel_context
from strands import Agent
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder

# Same models as the notebook: the Researcher keeps the Sonnet default (tool use is the hard
# step); the Analyst and Synthesizer only transform text, so they run on the smaller
# Claude Haiku 4.5, through its global inference profile.
SMALL_MODEL = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

# Mock business intelligence tools (a copy of ../../02-single-agent/decision_brief_tools.py,
# so the container is self-contained). Replace with a live data source, for example
# AgentCore Gateway with the Web Search connector:
# https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-web-search-tool.html
from mock_tools import get_company_data, get_market_benchmarks, get_competitor_data

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

RESEARCHER_PROMPT = '''You are a market research specialist.
Given a decision brief, gather relevant company data, market benchmarks,
and competitor intelligence using your tools.
Return structured findings: data only, no recommendations.'''

ANALYST_PROMPT = '''You are a business strategy analyst.
You receive the decision brief and the Researcher's findings. Analyze each option (A, B, C).
For each option return:
- Strengths and weaknesses
- Implementation complexity: Low / Medium / High (with one-sentence justification)
- Top 2 risks with specific mitigations
- Verdict: Proceed / Proceed with caution / Do not proceed
Cite the research numbers behind each verdict: the next stage does not see the raw research.
Return structured analysis only, no executive memo yet.'''

SYNTHESIZER_PROMPT = '''You are an executive communications specialist.
You receive the decision brief and the Analyst's option analyses (which cite the research).
Write a leadership memo:

## Decision Memo: [Title]
**Recommendation**: [one sentence: which option and why]

### Options at a Glance
| | Option A | Option B | Option C |
|---|---|---|---|
| Complexity | | | |
| Risk level | | | |
| Verdict | | | |

### Top 3 Risks & Mitigations
### Success Metrics (3-5 KPIs with targets)
### Decision Required: owner · deadline · approvers needed

Under 400 words. Be direct.'''


def build_chain():
    """Build the chain fresh per request, like the notebook, so no state leaks between requests."""
    researcher = Agent(
        tools=[get_company_data, get_market_benchmarks, get_competitor_data],
        system_prompt=RESEARCHER_PROMPT,
        callback_handler=None,
    )
    analyst = Agent(model=SMALL_MODEL, system_prompt=ANALYST_PROMPT, callback_handler=None)
    synthesizer = Agent(model=SMALL_MODEL, system_prompt=SYNTHESIZER_PROMPT, callback_handler=None)

    builder = GraphBuilder()
    builder.add_node(researcher,  "researcher")
    builder.add_node(analyst,     "analyst")
    builder.add_node(synthesizer, "synthesizer")
    builder.add_edge("researcher", "analyst")      # researcher → analyst
    builder.add_edge("analyst",    "synthesizer")  # analyst → synthesizer
    builder.set_execution_timeout(300)             # stop a runaway graph (Strands warns when no limit is set)
    return builder.build()


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt") if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")

    # OTEL: propagate the session ID across all spans.
    session_id = getattr(context, "session_id", None) or str(uuid.uuid4())
    token = otel_context.attach(baggage.set_baggage("session.id", session_id))
    logger.info("session.id=%s module=m3-sequential-chain", session_id)
    try:
        result = build_chain()(brief)
        return str(result.results["synthesizer"].result).strip()
    finally:
        otel_context.detach(token)


if __name__ == "__main__":
    app.run()
