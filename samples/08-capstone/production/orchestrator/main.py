"""
Capstone Orchestrator Runtime — A2A + AgentCore Memory.

Architecture:
  chat.py ──invoke_agent_runtime──► Orchestrator (HTTP, port 8080)
                                        │ A2AAgent (SigV4, port 9000)
                                        ├──► Researcher Runtime
                                        ├──► Analyzer Runtime ×3 (concurrent)
                                        └──► Critic-Refiner Runtime

Session management:
  sessionId : context.session_id (= runtimeSessionId) — routes to same container
  actorId   : context.request_headers X-Amzn-...-Custom-Actor-Id — LTM scope

Memory (when BEDROCK_AGENTCORE_MEMORY_ID is set):
  AgentCoreMemorySessionManager — stores STM events, extracts LTM facts per actorId.
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html

A2A calls run in isolated threads (asyncio.new_event_loop) to avoid conflicts
with BedrockAgentCoreApp's worker loop.
https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/#as-a-tool

Environment variables required:
  RESEARCHER_RUNTIME_ARN
  ANALYZER_RUNTIME_ARN
  CRITIC_REFINER_RUNTIME_ARN

Optional:
  BEDROCK_AGENTCORE_MEMORY_ID  — enables AgentCore Memory (STM + LTM)
  AWS_REGION                   — defaults to us-east-1
"""

import asyncio
import concurrent.futures
import logging
import os
import sys
import threading
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import BedrockAgentCoreContext
from strands import Agent, tool
from strands.agent.a2a_agent import A2AAgent

# a2a_utils.py is bundled alongside this file in the deployment ZIP
from a2a_utils import a2a_endpoint, build_agent_card, make_a2a_config

logger = logging.getLogger(__name__)
app    = BedrockAgentCoreApp()

REGION             = os.environ.get("AWS_REGION", "us-east-1")
MEMORY_ID          = os.environ.get("BEDROCK_AGENTCORE_MEMORY_ID")
RESEARCHER_ARN     = os.environ["RESEARCHER_RUNTIME_ARN"]
ANALYZER_ARN       = os.environ["ANALYZER_RUNTIME_ARN"]
CRITIC_REFINER_ARN = os.environ["CRITIC_REFINER_RUNTIME_ARN"]

ACTOR_HEADER = "x-amzn-bedrock-agentcore-runtime-custom-actor-id"

ORCHESTRATOR_PROMPT = (
    "You coordinate the Capstone Decision-Memo pipeline. Execute ALL steps:\n"
    "1. Call researcher_agent with the full decision brief.\n"
    "2. Call parallel_analyzers with the brief and research (runs Options A/B/C simultaneously).\n"
    "3. Call critic_refiner with the brief and all analyses.\n"
    "Execute all three steps in sequence. Do not skip any step."
)

# ── Per-session state ──────────────────────────────────────────────────────────
# Keyed by session_id so each session has isolated history and actor identity.
# Prevents actor ID contamination and conversation history leaks across sessions.
_researchers:   dict[str, "A2AAgent"] = {}
_analyzers:     dict[str, "A2AAgent"] = {}
_critic_refs:   dict[str, "A2AAgent"] = {}
_orchestrators: dict[str, "Agent"]    = {}


def _current_session() -> tuple:
    """Return (session_id, actor_id) from the current request context.
    Read on every invocation — never cached globally.
    """
    import uuid
    headers    = BedrockAgentCoreContext.get_request_headers() or {}
    actor_id   = headers.get(ACTOR_HEADER) or "default-user"
    session_id = BedrockAgentCoreContext.get_session_id() or str(uuid.uuid4())
    return session_id, actor_id


def _get_researcher(sid: str, aid: str) -> A2AAgent:
    if sid not in _researchers:
        agent = A2AAgent(
            endpoint=a2a_endpoint(RESEARCHER_ARN, REGION),
            client_config=make_a2a_config(aid, REGION),
            name="researcher",
            description="Market research specialist.",
        )
        agent._agent_card = build_agent_card(RESEARCHER_ARN, "researcher",
            "Market research specialist.", REGION)
        _researchers[sid] = agent
    return _researchers[sid]


def _get_analyzer(sid: str, aid: str) -> A2AAgent:
    if sid not in _analyzers:
        agent = A2AAgent(
            endpoint=a2a_endpoint(ANALYZER_ARN, REGION),
            client_config=make_a2a_config(aid, REGION),
            name="analyzer",
            description="Evaluates one decision option.",
        )
        agent._agent_card = build_agent_card(ANALYZER_ARN, "analyzer",
            "Evaluates one decision option.", REGION)
        _analyzers[sid] = agent
    return _analyzers[sid]


def _get_critic_refiner(sid: str, aid: str) -> A2AAgent:
    if sid not in _critic_refs:
        agent = A2AAgent(
            endpoint=a2a_endpoint(CRITIC_REFINER_ARN, REGION),
            client_config=make_a2a_config(aid, REGION),
            name="critic_refiner",
            description="Writer-Critic quality loop for decision memos.",
        )
        agent._agent_card = build_agent_card(CRITIC_REFINER_ARN, "critic_refiner",
            "Writer-Critic quality loop for decision memos.", REGION)
        _critic_refs[sid] = agent
    return _critic_refs[sid]


def _call_a2a(agent: A2AAgent, prompt: str, timeout: int = 600) -> str:
    """Call A2AAgent in an isolated thread with a fresh event loop.

    Prevents 'Event loop is closed' errors that occur when A2AAgent's
    run_async() conflicts with BedrockAgentCoreApp's worker event loop.
    """
    from a2a_utils import extract_a2a_text
    result_holder: list = [None, None]

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


# ── @tool definitions ──────────────────────────────────────────────────────────

@tool
def researcher_agent(topic: str) -> str:
    """Research market context, company data, benchmarks, and competitive intelligence.
    Call this FIRST with the full decision brief.
    Args:
        topic: The decision topic to research.
    """
    sid, aid = _current_session()
    return _call_a2a(_get_researcher(sid, aid), topic)


@tool
def parallel_analyzers(brief: str, research_context: str) -> str:
    """Run all three option analyzers (A, B, C) simultaneously using the Analyzer Runtime.
    Call this SECOND after researcher_agent.
    Args:
        brief: The original decision brief.
        research_context: Findings from researcher_agent.
    """
    prompts = [
        f"Option A ($19.99 invite-only)\nBrief: {brief}\nResearch: {research_context}",
        f"Option B ($14.99 5% pilot)\nBrief: {brief}\nResearch: {research_context}",
        f"Option C ($12.99 full launch)\nBrief: {brief}\nResearch: {research_context}",
    ]
    # Run 3 concurrent A2A calls via ThreadPoolExecutor (each in its own event loop)
    sid, aid = _current_session()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(_call_a2a, _get_analyzer(sid, aid), p) for p in prompts]
        results = [f.result(timeout=600) for f in futures]
    ra, rb, rc = results
    return f"OPTION A:\n{ra}\n\nOPTION B:\n{rb}\n\nOPTION C:\n{rc}"


@tool
def critic_refiner(brief: str, analyses: str) -> str:
    """Run the Writer-Critic quality loop via the Critic-Refiner Runtime.
    Call this THIRD and LAST after parallel_analyzers.
    Args:
        brief: The original decision brief.
        analyses: Combined analyses from parallel_analyzers.
    """
    sid, aid = _current_session()
    return _call_a2a(
        _get_critic_refiner(sid, aid),
        f"Brief:\n{brief}\n\nAnalyses:\n{analyses}",
    )


def _get_orchestrator(sid: str, aid: str) -> Agent:
    """Per-session Agent — isolated history and actor identity per session.
    Prevents conversation history leaks across different users/sessions.
    Uses AgentCoreMemorySessionManager if MEMORY_ID is set, else SlidingWindow.
    """
    if sid not in _orchestrators:
        if MEMORY_ID:
            from bedrock_agentcore.memory.integrations.strands.config import (
                AgentCoreMemoryConfig, RetrievalConfig,
            )
            from bedrock_agentcore.memory.integrations.strands.session_manager import (
                AgentCoreMemorySessionManager,
            )
            memory_config = AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=sid,
                actor_id=aid,
                retrieval_config={
                    f"/facts/{aid}": RetrievalConfig(top_k=5, relevance_score=0.4),
                },
            )
            session_mgr = AgentCoreMemorySessionManager(memory_config, REGION)
            _orchestrators[sid] = Agent(
                tools=[researcher_agent, parallel_analyzers, critic_refiner],
                system_prompt=ORCHESTRATOR_PROMPT,
                session_manager=session_mgr,
                callback_handler=None,
            )
        else:
            from strands.agent.conversation_manager import SlidingWindowConversationManager
            _orchestrators[sid] = Agent(
                tools=[researcher_agent, parallel_analyzers, critic_refiner],
                system_prompt=ORCHESTRATOR_PROMPT,
                conversation_manager=SlidingWindowConversationManager(window_size=20),
                callback_handler=None,
            )
    return _orchestrators[sid]


@app.entrypoint
def invoke(payload, context):
    brief = payload.get("prompt", payload) if isinstance(payload, dict) else payload
    if not brief:
        raise ValueError("Missing required field: prompt")
    sid, aid = _current_session()
    return str(_get_orchestrator(sid, aid)(brief)).strip()


if __name__ == "__main__":
    app.run()
