"""Legal Agent specialist — A2A Runtime."""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a legal and compliance reviewer. Review the investment brief for: "
    "regulatory risks, data privacy concerns (GDPR, CCPA), contractual obligations, "
    "IP considerations, and red flags for due diligence. "
    "Return a bullet-point list of legal risks with severity (High/Medium/Low). 150 words max."
)

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
