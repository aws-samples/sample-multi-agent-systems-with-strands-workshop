"""Synthesizer specialist Runtime.
Receives brief + all analyses and writes the executive leadership memo.
Deployed independently: called last by the Orchestrator Runtime.
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

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


def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not prompt:
        raise ValueError("Missing required field: prompt")
    return str(get_agent()(prompt)).strip()


if __name__ == "__main__":
    app.run()
