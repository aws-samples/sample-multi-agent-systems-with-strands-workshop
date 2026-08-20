"""
Agent-as-Tool Orchestrator Runtime (Pattern 5).

Specialists: Research Agent, Finance Agent, Legal Agent, Writer Agent.
Each specialist is an A2A Runtime wrapped as a @tool.
The orchestrator LLM (Agent) decides which specialists to call and in what order.

  User ──invoke_agent_runtime──► Orchestrator (HTTP, port 8080)
                                      │ A2AAgent (SigV4, port 9000)
                                      ├──► Research Agent Runtime
                                      ├──► Finance Agent Runtime
                                      ├──► Legal Agent Runtime
                                      └──► Writer Agent Runtime

Strands Agent-as-Tool:
  https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/#as-a-tool
AWS AgentCore A2A:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
"""
import asyncio
import logging
import os
import threading
import uuid
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager

import sys
sys.path = [str(Path(__file__).parent)] + sys.path
from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config, extract_a2a_text

logger = logging.getLogger(__name__)
app    = BedrockAgentCoreApp()

REGION           = os.environ.get("AWS_REGION", "us-east-1")
RESEARCH_ARN     = os.environ["RESEARCH_RUNTIME_ARN"]
FINANCE_ARN      = os.environ["FINANCE_RUNTIME_ARN"]
LEGAL_ARN        = os.environ["LEGAL_RUNTIME_ARN"]
WRITER_ARN       = os.environ["WRITER_RUNTIME_ARN"]

ORCHESTRATOR_PROMPT = (
    "You are an investment committee coordinator. For each investment request:\n"
    "1. Call research_agent to gather company and market data.\n"
    "2. Call finance_agent with the brief and research findings.\n"
    "3. Call legal_agent with the brief to identify legal and compliance risks.\n"
    "4. Call writer_agent with all findings to produce the final investment memo.\n"
    "Execute all four steps. Pass relevant context from each specialist to the next."
)

_research_agents: dict = {}
_finance_agents:  dict = {}
_legal_agents:    dict = {}
_writer_agents:   dict = {}
_session_agents:  dict = {}
_session_lock     = threading.Lock()


def _call_a2a(agent, prompt: str, timeout: int = 600) -> str:
    result_holder: list = [None, None]
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_holder[0] = loop.run_until_complete(agent.invoke_async(prompt))
        except Exception as exc:
            result_holder[1] = exc
        finally:
            loop.close()
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        raise TimeoutError(f"A2A call timed out after {timeout}s")
    if result_holder[1] is not None:
        raise result_holder[1]
    return extract_a2a_text(result_holder[0])


def _get_a2a(cache, arn, name, desc):
    if arn not in cache:
        from strands.agent.a2a_agent import A2AAgent
        a = A2AAgent(endpoint=a2a_endpoint(arn, REGION),
                     client_config=make_a2a_config(region=REGION),
                     name=name, description=desc)
        a._agent_card = build_agent_card(arn, name, desc, REGION)
        cache[arn] = a
    return cache[arn]


@tool
def research_agent(topic: str) -> str:
    """Gather market data, company metrics, and competitive intelligence for an investment topic.

    Args:
        topic: The company or investment topic to research
    """
    return _call_a2a(_get_a2a(_research_agents, RESEARCH_ARN, "research",
                               "Market research and competitive intelligence specialist."), topic)


@tool
def finance_agent(brief: str, research_context: str) -> str:
    """Analyze financial viability: ROI, unit economics, projections, and investment verdict.

    Args:
        brief: The original investment brief
        research_context: Market and company data from research_agent
    """
    return _call_a2a(_get_a2a(_finance_agents, FINANCE_ARN, "finance",
                               "Financial analyst — ROI, unit economics, investment verdict."),
                     f"Brief:\n{brief}\n\nResearch:\n{research_context}")


@tool
def legal_agent(brief: str) -> str:
    """Review legal and compliance risks: regulatory, data privacy, IP, due diligence flags.

    Args:
        brief: The investment brief to review
    """
    return _call_a2a(_get_a2a(_legal_agents, LEGAL_ARN, "legal",
                               "Legal and compliance reviewer — risks and due diligence flags."), brief)


@tool
def writer_agent(brief: str, research_context: str, financial_analysis: str, legal_review: str) -> str:
    """Write the final investment memo. Call LAST — after all other specialists.

    Args:
        brief: The original investment brief
        research_context: Findings from research_agent
        financial_analysis: Analysis from finance_agent
        legal_review: Risk review from legal_agent
    """
    return _call_a2a(_get_a2a(_writer_agents, WRITER_ARN, "writer",
                               "Investment memo writer — synthesizes all findings."),
                     f"Brief:\n{brief}\n\nResearch:\n{research_context}\n\n"
                     f"Financial:\n{financial_analysis}\n\nLegal:\n{legal_review}")


def _get_session_agent(session_id: str) -> Agent:
    with _session_lock:
        if session_id not in _session_agents:
            _session_agents[session_id] = Agent(
                tools=[research_agent, finance_agent, legal_agent, writer_agent],
                system_prompt=ORCHESTRATOR_PROMPT,
                conversation_manager=SlidingWindowConversationManager(window_size=20),
                callback_handler=None,
            )
        return _session_agents[session_id]


@app.entrypoint
def invoke(payload, context):
    import time
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    session_id = (context.session_id if context and context.session_id else None) or str(uuid.uuid4())
    last_error = None
    for attempt in range(3):
        try:
            result_str = str(_get_session_agent(session_id)(brief)).strip()
            if "Agent execution failed" in result_str:
                raise RuntimeError(f"Agent failed (cold start?): {result_str[:200]}")
            return result_str
        except Exception as exc:
            last_error = exc
            _session_agents.pop(session_id, None)
            logger.warning("Attempt %d failed: %s — retrying in %ds", attempt+1, exc, 10*(attempt+1))
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
    raise last_error


if __name__ == "__main__":
    app.run()
