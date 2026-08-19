"""
Synthesizer specialist — A2A Runtime (Pattern 5: Agent-as-Tool).

Writes the final leadership memo combining research and analysis.
Serves on port 9000 using the A2A protocol.
"""
import logging

from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an executive communications specialist. Write a leadership memo:\n"
    "## Recommendation (one sentence: which option and why)\n"
    "## Options at a Glance (table comparing A, B, C)\n"
    "## Top 3 Risks with specific mitigations\n"
    "## Success Metrics (at least 2 KPIs with numeric targets)\n"
    "## Decision Required (owner, deadline, who approves)\n"
    "Under 400 words."
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
