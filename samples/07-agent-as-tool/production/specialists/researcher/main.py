"""
Researcher specialist — A2A Runtime (Pattern 5: Agent-as-Tool).

Serves on port 9000 using the A2A protocol. The Orchestrator Runtime
calls this specialist via A2AAgent with SigV4 auth.

Strands A2A server:
  https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/
AWS AgentCore A2A:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
"""
import logging

from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from mock_tools import get_company_data, get_competitor_data, get_market_benchmarks

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a market research specialist. "
    "Use your tools to gather company data, industry benchmarks, and competitor "
    "intelligence. Return structured findings — data only, no recommendations."
)

_agent = None


def get_agent() -> Agent:
    """Lazy singleton — one Agent per container lifetime."""
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
