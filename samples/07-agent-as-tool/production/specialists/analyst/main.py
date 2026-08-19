"""
Analyst specialist — A2A Runtime (Pattern 5: Agent-as-Tool).

Evaluates decision options A/B/C based on research findings.
Serves on port 9000 using the A2A protocol.
"""
import logging

from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a business strategy analyst. "
    "Evaluate each option (A, B, C) based on: strengths, weaknesses, "
    "implementation complexity (Low/Med/High), top 2 risks with mitigations, "
    "and a verdict. Return structured analysis."
)

_agent = None


def get_agent() -> Agent:
    """Lazy singleton — one Agent per container lifetime."""
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent


if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
