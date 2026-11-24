"""Analyst specialist — A2A Runtime (Pattern 1: Sequential Chain)."""
import logging
import os

import boto3
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.models import BedrockModel
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

# Same model as the notebook: this stage only transforms text, so it runs on Amazon Nova Pro.
# Nova Pro is called through its cross-region inference profile (us./eu./apac.):
# the bare "amazon.nova-pro-v1:0" is rejected on-demand in most regions.
region = os.environ.get("AWS_REGION") or boto3.Session().region_name
geo = {"us": "us", "eu": "eu", "ap": "apac"}.get(region.split("-")[0])
NOVA_PRO = BedrockModel(model_id=f"{geo}.amazon.nova-pro-v1:0") if geo else None  # None → Sonnet default

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
        _agent = Agent(model=NOVA_PRO, system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    # This file runs on Amazon Bedrock AgentCore Runtime — not locally.
    # Running it locally starts a server on port 9000 that requires
    # AgentCore authentication to work. Deploy with deploy.py instead.
    serve_a2a(StrandsA2AExecutor(get_agent()))
