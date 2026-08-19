"""Analyzer specialist Runtime (single option).
Receives one decision option + research context and returns a structured assessment.
Deployed as ONE Runtime: called 3 times in parallel (Options A, B, C) by the Orchestrator.
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

SYSTEM_PROMPT = (
    "You are a business strategy analyst. Evaluate the ONE option you are given: "
    "strengths, weaknesses, complexity (Low/Med/High), "
    "top 2 risks with specific mitigations, verdict. 150 words max."
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
