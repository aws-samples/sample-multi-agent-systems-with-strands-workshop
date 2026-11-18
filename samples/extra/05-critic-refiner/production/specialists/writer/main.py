"""Writer (Generator) specialist — A2A Runtime.
Produces or revises a leadership memo based on the brief and optional feedback.
"""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an executive memo writer. Write or revise a COMPLETE leadership memo "
    "with exactly these 5 sections:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table comparing A, B, C on Complexity/Risk/Verdict)\n"
    "## Top 3 Risks (each with a specific mitigation)\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, who must approve)\n"
    "If you receive revision feedback, address ALL flagged criteria. Under 400 words."
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
