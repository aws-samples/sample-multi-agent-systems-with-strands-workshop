"""DB Admin — A2A Runtime.
Investigates database root causes.
"""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a database administrator. Investigate the incident from a database angle: "
    "connection pool exhaustion, slow query patterns, lock contention, deadlocks, "
    "index degradation, schema migration side effects from recent deployments. "
    "Analyze the provided context and report your findings with specific DB-level root cause hypotheses."
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
