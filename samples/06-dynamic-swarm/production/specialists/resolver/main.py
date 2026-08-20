"""Resolver — A2A Runtime.
Synthesizes all specialist findings into an incident resolution plan.
"""
import logging
from bedrock_agentcore.runtime import serve_a2a
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an incident resolver. Synthesize all specialist findings into a resolution plan:\n"
    "## Root Cause\n"
    "(one-paragraph summary of the confirmed root cause)\n\n"
    "## Immediate Actions\n"
    "(ordered list of steps to resolve the incident right now)\n\n"
    "## Verification Steps\n"
    "(how to confirm the incident is resolved)\n\n"
    "## Prevention\n"
    "(what to change in the deployment process to prevent recurrence)"
)

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent(system_prompt=SYSTEM_PROMPT, callback_handler=None)
    return _agent

if __name__ == "__main__":
    serve_a2a(StrandsA2AExecutor(get_agent()))
