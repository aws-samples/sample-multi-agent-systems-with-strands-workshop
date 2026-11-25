"""Analyst specialist — A2A Runtime (Pattern 1: Sequential Chain)."""
import logging

from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.models import BedrockModel
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

# Same model as the notebook: Amazon Nova Lite. In a graph the edges do the routing, so each
# agent only does one narrow job and a smaller model is enough. max_tokens: Strands has no
# output limit on record for Nova, and Bedrock's default can cut a long answer short.
MODEL = BedrockModel(model_id="amazon.nova-lite-v1:0", max_tokens=5000)

# Same prompt as the local notebook (module-03.ipynb).
SYSTEM_PROMPT = '''You are a business strategy analyst.
You receive the decision brief and the Researcher's findings. Analyze each option (A, B, C).
For each option return:
- Strengths and weaknesses
- Implementation complexity: Low / Medium / High (with one-sentence justification)
- Top 2 risks with specific mitigations
- Verdict: Proceed / Proceed with caution / Do not proceed
Cite the research numbers behind each verdict: the next stage does not see the raw research.
Return structured analysis only, no executive memo yet.'''

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(model=MODEL, system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    # This file runs on Amazon Bedrock AgentCore Runtime — not locally.
    # Running it locally starts a server on port 9000 that requires
    # AgentCore authentication to work. Deploy with deploy.py instead.
    serve_a2a(StrandsA2AExecutor(get_agent()))
