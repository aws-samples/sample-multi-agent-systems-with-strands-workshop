"""Writer Agent specialist — A2A Runtime."""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an investment memo writer. Produce a professional investment analysis memo:\n"
    "## Executive Summary (recommendation in one sentence)\n"
    "## Market Opportunity (size, growth, competitive position)\n"
    "## Financial Highlights (key metrics, ROI, projections)\n"
    "## Risk Assessment (top 3 risks with mitigations)\n"
    "## Recommendation (Invest / Pass, terms, conditions)\n"
    "Under 450 words. Be direct."
)

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
