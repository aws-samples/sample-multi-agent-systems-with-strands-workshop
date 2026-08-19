"""Synthesizer specialist — A2A Runtime (Pattern 1: Sequential Chain)."""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Write a leadership memo: Recommendation, Options table A/B/C, "
    "Top 3 Risks, Success Metrics, Decision Required. Under 400 words."
)

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
