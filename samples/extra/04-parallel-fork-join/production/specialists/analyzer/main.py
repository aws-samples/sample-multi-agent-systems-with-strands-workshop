"""Analyzer specialist — A2A Runtime (called 3x in parallel for A/B/C)."""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = (
    "You are a business strategy analyst. Evaluate the ONE option you receive: "
    "strengths, weaknesses, complexity (Low/Med/High), top 2 risks with mitigations, verdict. 150 words max."
)
_agent = None
def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent
if __name__ == "__main__":
    # This file runs on Amazon Bedrock AgentCore Runtime — not locally.
    # Running it locally starts a server on port 9000 that requires
    # AgentCore authentication to work. Deploy with deploy.py instead.
    serve_a2a(StrandsA2AExecutor(get_agent()))
