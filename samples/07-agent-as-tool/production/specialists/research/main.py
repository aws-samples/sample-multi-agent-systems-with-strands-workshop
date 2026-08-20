"""Research Agent specialist — A2A Runtime."""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from mock_tools import get_company_data, get_market_benchmarks, get_competitor_data

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a market research specialist. Use your tools to gather company data, "
    "industry benchmarks, and competitive intelligence. Return structured findings: data only."
)

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            tools=[get_company_data, get_market_benchmarks, get_competitor_data],
            system_prompt=SYSTEM_PROMPT,
            callback_handler=None,
        )
    return _agent

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
