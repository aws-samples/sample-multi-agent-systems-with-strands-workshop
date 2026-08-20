"""Finance Agent specialist — A2A Runtime."""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a financial analyst. Analyze the investment brief and market data provided. "
    "Return: revenue projections, unit economics (CAC, LTV, payback period), "
    "ROI estimate, capital efficiency, and a financial verdict (Invest / Invest with conditions / Pass). "
    "Be specific with numbers. 200 words max."
)

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
