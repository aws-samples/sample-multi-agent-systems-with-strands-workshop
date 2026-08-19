"""Analyst specialist Runtime.
Receives a decision brief + research context and returns structured analysis of all options.
Deployed independently: called by the Orchestrator Runtime.
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

SYSTEM_PROMPT = (
    "You are a business strategy analyst. Evaluate each option (A, B, C) based on: "
    "strengths, weaknesses, implementation complexity (Low/Med/High), "
    "top 2 risks with mitigations, and a verdict. Return structured analysis."
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
