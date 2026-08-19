"""
Agent-as-Tool Orchestrator Runtime (Pattern 5).

Receives user calls via BedrockAgentCoreApp (port 8080 / HTTP protocol).
Delegates to specialist A2A Runtimes via A2AAgent with SigV4 auth.

Architecture:
  chat.py ──invoke_agent_runtime──► Orchestrator (HTTP, port 8080)
                                        │ A2AAgent (SigV4, port 9000)
                                        ├──► Researcher Runtime
                                        ├──► Analyst Runtime
                                        └──► Synthesizer Runtime

Session management:
  sessionId  : from context.session_id (= runtimeSessionId, routes to same container)
  actorId    : from context.request_headers X-Amzn-...-Custom-Actor-Id
               Propagated to specialists via AgentCoreA2AAuth on each A2A call.

Strands Agent-as-Tool:
  https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/#as-a-tool
AWS AgentCore A2A:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
"""
import asyncio
import logging
import os
import sys
import threading
import uuid
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
# A2AAgent imported lazily inside _get_researcher/_get_analyst/_get_synthesizer
from strands.agent.conversation_manager import SlidingWindowConversationManager

# A2A imports deferred to first call — avoids 30s cold-start timeout loading heavy libs

logger = logging.getLogger(__name__)
app    = BedrockAgentCoreApp()

REGION          = os.environ.get("AWS_REGION", "us-east-1")
RESEARCHER_ARN  = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYST_ARN     = os.environ["ANALYST_RUNTIME_ARN"]
SYNTHESIZER_ARN = os.environ["SYNTHESIZER_RUNTIME_ARN"]

ORCHESTRATOR_PROMPT = (
    "You are an orchestrator using the Agent-as-Tool pattern. "
    "Coordinate these three specialists in this order:\n"
    "1. Call researcher_agent with the full decision brief.\n"
    "2. Call analyst_agent with the brief and research findings.\n"
    "3. Call synthesizer_agent with the brief, research, and analysis.\n"
    "Execute all three steps. Pass outputs from one step as inputs to the next."
)

# ── Singletons — one per container lifetime ───────────────────────────────────
_researcher  = None
_analyst     = None
_synthesizer = None

# Per-session orchestrators keyed by session_id; each gets its own
# SlidingWindowConversationManager so history never leaks across users.
_session_agents: dict = {}
_session_lock         = threading.Lock()


def _call_a2a(agent, prompt: str, timeout: int = 600) -> str:
    """Call A2AAgent in an isolated thread with a fresh event loop.

    BedrockAgentCoreApp runs the entrypoint in its own worker event loop.
    Calling A2AAgent.__call__ (which internally uses run_async) from inside
    that loop causes 'Event loop is closed' errors. Running in a fresh thread
    with asyncio.new_event_loop() avoids this conflict entirely.

    Strands A2A: https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/
    """
    from a2a_utils import extract_a2a_text
    result_holder: list = [None, None]  # [result, exception]

    def _run() -> None:
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


def _get_researcher():
    global _researcher
    if _researcher is None:
        from strands.agent.a2a_agent import A2AAgent
        from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config
        agent = A2AAgent(
            endpoint=a2a_endpoint(RESEARCHER_ARN, REGION),
            client_config=make_a2a_config(region=REGION),
            name="researcher",
            description="Market research specialist.",
        )
        # Pre-populate to skip unauthenticated GET /.well-known/agent-card.json
        agent._agent_card = build_agent_card(RESEARCHER_ARN, "researcher",
            "Market research specialist.", REGION)
        _researcher = agent
    return _researcher


def _get_analyst():
    global _analyst
    if _analyst is None:
        from strands.agent.a2a_agent import A2AAgent
        from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config
        agent = A2AAgent(
            endpoint=a2a_endpoint(ANALYST_ARN, REGION),
            client_config=make_a2a_config(region=REGION),
            name="analyst",
            description="Business strategy analyst.",
        )
        agent._agent_card = build_agent_card(ANALYST_ARN, "analyst",
            "Business strategy analyst.", REGION)
        _analyst = agent
    return _analyst


def _get_synthesizer():
    global _synthesizer
    if _synthesizer is None:
        from strands.agent.a2a_agent import A2AAgent
        from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config
        agent = A2AAgent(
            endpoint=a2a_endpoint(SYNTHESIZER_ARN, REGION),
            client_config=make_a2a_config(region=REGION),
            name="synthesizer",
            description="Executive memo writer.",
        )
        agent._agent_card = build_agent_card(SYNTHESIZER_ARN, "synthesizer",
            "Executive memo writer.", REGION)
        _synthesizer = agent
    return _synthesizer


# ── @tool functions — wrap A2AAgent calls ────────────────────────────────────

@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitive intelligence.
    Call this FIRST with the full decision brief.
    Args:
        topic: The decision topic to research.
    """
    return _call_a2a(_get_researcher(), topic)


@tool
def analyst_agent(brief: str, research_context: str) -> str:
    """Analyze all decision options (A, B, C) using the research findings.
    Call this SECOND after researcher_agent.
    Args:
        brief: The original decision brief.
        research_context: Findings from researcher_agent.
    """
    return _call_a2a(_get_analyst(), f"Brief:\n{brief}\n\nResearch findings:\n{research_context}")


@tool
def synthesizer_agent(brief: str, research_context: str, analysis: str) -> str:
    """Write the final leadership memo combining research and analysis.
    Call this THIRD and LAST after analyst_agent.
    Args:
        brief: The original decision brief.
        research_context: Findings from researcher_agent.
        analysis: Analysis from analyst_agent.
    """
    return _call_a2a(_get_synthesizer(), f"Brief:\n{brief}\n\nResearch:\n{research_context}\n\nAnalysis:\n{analysis}")


def _get_session_agent(session_id: str) -> Agent:
    """Return a per-session Agent with isolated conversation history."""
    with _session_lock:
        if session_id not in _session_agents:
            _session_agents[session_id] = Agent(
                tools=[researcher_agent, analyst_agent, synthesizer_agent],
                system_prompt=ORCHESTRATOR_PROMPT,
                conversation_manager=SlidingWindowConversationManager(window_size=20),
                callback_handler=None,
            )
        return _session_agents[session_id]


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    session_id = (context.session_id if context and context.session_id else None) or str(uuid.uuid4())
    return str(_get_session_agent(session_id)(brief)).strip()


if __name__ == "__main__":
    app.run()
