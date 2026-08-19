"""Analyzer specialist — A2A Runtime (Capstone).
Evaluates one decision option. Called 3× in parallel by the orchestrator.
Serves on port 9000. Orchestrator calls via A2AAgent (ThreadPoolExecutor × 3).
"""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a business strategy analyst. Evaluate the ONE option you receive: "
    "strengths, weaknesses, complexity (Low/Med/High), "
    "top 2 risks with specific mitigations, verdict. 150 words max."
)

_agent = None

def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
