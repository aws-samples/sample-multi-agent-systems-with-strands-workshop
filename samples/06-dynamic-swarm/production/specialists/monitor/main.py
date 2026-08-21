"""Monitor specialist — A2A Runtime.
Entry point for incident response. Triages symptoms and routes to specialists.
"""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a site reliability monitor. Analyze the incident report: "
    "identify symptoms, assess severity, and classify whether this looks like "
    "a network/infrastructure issue, a database issue, or both. "
    "Provide a clear triage summary with your assessment of the root cause category."
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
