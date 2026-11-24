"""Synthesizer specialist — A2A Runtime (Pattern 1: Sequential Chain)."""
import logging

from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.models import BedrockModel
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

# Same model as the notebook: this stage only transforms text, so it runs on the smaller
# Claude Haiku 4.5, through its global inference profile.
SMALL_MODEL = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

# Same prompt as the local notebook (module-03.ipynb).
SYSTEM_PROMPT = '''You are an executive communications specialist.
You receive the decision brief and the Analyst's option analyses (which cite the research).
Write a leadership memo:

## Decision Memo: [Title]
**Recommendation**: [one sentence: which option and why]

### Options at a Glance
| | Option A | Option B | Option C |
|---|---|---|---|
| Complexity | | | |
| Risk level | | | |
| Verdict | | | |

### Top 3 Risks & Mitigations
### Success Metrics (3-5 KPIs with targets)
### Decision Required: owner · deadline · approvers needed

Under 400 words. Be direct.'''

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(model=SMALL_MODEL, system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    # This file runs on Amazon Bedrock AgentCore Runtime — not locally.
    # Running it locally starts a server on port 9000 that requires
    # AgentCore authentication to work. Deploy with deploy.py instead.
    serve_a2a(StrandsA2AExecutor(get_agent()))
