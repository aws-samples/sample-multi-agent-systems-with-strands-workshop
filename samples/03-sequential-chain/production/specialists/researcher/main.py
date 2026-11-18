"""Researcher specialist — A2A Runtime (Pattern 1: Sequential Chain)."""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from mock_tools import get_company_data, get_competitor_data, get_market_benchmarks

logger = logging.getLogger(__name__)

# Same prompt as the local notebook (module-03.ipynb).
SYSTEM_PROMPT = '''You are a market research specialist.
Given a decision brief, gather relevant company data, market benchmarks,
and competitor intelligence using your tools.
Return structured findings: data only, no recommendations.'''

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
    # This file runs on Amazon Bedrock AgentCore Runtime — not locally.
    # Running it locally starts a server on port 9000 that requires
    # AgentCore authentication to work. Deploy with deploy.py instead.
    serve_a2a(StrandsA2AExecutor(get_agent()))
