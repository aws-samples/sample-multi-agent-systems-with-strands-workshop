"""Critic specialist — A2A Runtime.
Evaluates a memo against 5 criteria. Returns APPROVED or REVISION NEEDED.
"""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a quality critic. Check ONLY these 5 criteria:\n"
    "1. '## Recommendation' — clear option choice (A, B, or C)\n"
    "2. '## Options at a Glance' — table comparing A, B, C\n"
    "3. '## Top 3 Risks' — at least 3 risks each with a specific mitigation\n"
    "4. '## Success Metrics' — at least 2 KPIs with numeric targets\n"
    "5. '## Decision Required' — both owner AND deadline\n"
    "Respond with EXACTLY one of:\n"
    "APPROVED\n"
    "REVISION NEEDED: [which criterion numbers are missing or incomplete]\n"
    "Your response must start with APPROVED or REVISION NEEDED."
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
