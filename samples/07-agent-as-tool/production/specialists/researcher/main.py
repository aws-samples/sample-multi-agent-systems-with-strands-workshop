"""Researcher specialist Runtime.
Receives a research topic and returns structured market findings.
Deployed independently: called by the Orchestrator Runtime.
"""
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from mock_tools import get_company_data, get_market_benchmarks, get_competitor_data

logger = logging.getLogger(__name__)
app = BedrockAgentCoreApp()

SYSTEM_PROMPT = (
    "You are a market research specialist. Use your tools to gather company data, "
    "industry benchmarks, and competitor intelligence. Return structured findings: data only."
)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            tools=[get_company_data, get_market_benchmarks, get_competitor_data],
            system_prompt=SYSTEM_PROMPT,
            callback_handler=None,
        )
    return _agent


@app.entrypoint
def invoke(payload, context):
    topic = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not topic:
        raise ValueError("Missing required field: prompt")
    return str(get_agent()(topic)).strip()


if __name__ == "__main__":
    app.run()
